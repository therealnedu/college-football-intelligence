"""Load one season of teams, games, and season stats.

The load is idempotent: a second run replaces games and stats for that season
and origin, and updates teams in place. It does not insert a second copy.

Live mode spends at most three CollegeFootballData.com calls for the season
(teams, games, season stats) and pauses between them. A `Retry-After` longer
than 30 seconds is already refused by the HTTP client. If the remaining-quota
header drops below the configured guard, later resources are not requested.

A successful refresh inside the cache TTL is skipped unless `force` is set.
Cache hits are not new provider calls. Refresh-log rows are an audit of
attempts, so a forced rerun adds rows and still does not duplicate the data.
"""

import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.catalog import Catalog
from app.cfbd import CfbdClient, CfbdResult
from app.config import Settings
from app.errors import AppError
from app.fixtures_loader import load_fixture_list
from app.normalize import normalize_games, normalize_stats, normalize_teams

RESOURCES = ("teams", "games", "season_stats")


@dataclass
class ResourceReport:
    resource: str
    status: str
    records_written: int = 0
    http_status: int | None = None
    error_code: str | None = None
    detail: str | None = None
    rate_limit_remaining: str | None = None


@dataclass
class IngestReport:
    season: int
    data_mode: str
    provider_calls: int = 0
    stopped_early: bool = False
    resources: list[ResourceReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(item.status != "error" for item in self.resources)


def run_ingest(
    db: Session,
    settings: Settings,
    client: CfbdClient,
    season: int,
    *,
    force: bool = False,
    pause_seconds: float | None = None,
    sleeper=time.sleep,
    min_remaining: int | None = None,
) -> IngestReport:
    if season < settings.cfip_min_season or season > settings.max_season:
        raise AppError(
            "SEASON_OUT_OF_RANGE",
            f"Season must be from {settings.cfip_min_season} through {settings.max_season}.",
            422,
        )
    catalog = Catalog(db, settings, client)
    pause = settings.cfip_ingest_pause_seconds if pause_seconds is None else pause_seconds
    guard = settings.cfip_ingest_min_remaining if min_remaining is None else min_remaining
    classification = "" if settings.fixture_mode else settings.cfip_ingest_classification.strip()
    report = IngestReport(season=season, data_mode="fixture" if settings.fixture_mode else "live")
    calls = {"n": 0}

    teams_report = _load_teams(
        catalog,
        settings,
        client,
        season,
        classification,
        force,
        calls,
    )
    report.resources.append(teams_report)
    report.provider_calls = calls["n"]
    if teams_report.status == "error":
        return report
    if _quota_stop(teams_report, guard):
        return _stop_after(report, ("games", "season_stats"))

    if _should_pause(teams_report):
        _pause(pause, sleeper)

    games_report = _load_games(
        catalog,
        settings,
        client,
        season,
        classification,
        force,
        calls,
    )
    report.resources.append(games_report)
    report.provider_calls = calls["n"]
    if games_report.status == "error":
        return report
    if _quota_stop(games_report, guard):
        return _stop_after(report, ("season_stats",))

    if _should_pause(games_report):
        _pause(pause, sleeper)

    stats_report = _load_stats(
        catalog,
        settings,
        client,
        season,
        classification,
        force,
        calls,
    )
    report.resources.append(stats_report)
    report.provider_calls = calls["n"]
    return report


def _load_teams(catalog, settings, client, season, classification, force, calls) -> ResourceReport:
    if not force and catalog._fresh_refresh("teams", season, None) is not None:
        return ResourceReport(resource="teams", status="skipped", detail="Fresh cache.")
    started = time.perf_counter()
    try:
        payload, result = _teams_payload(settings, client, season, calls)
        teams, _skipped = normalize_teams(payload)
        if classification:
            wanted = classification.casefold()
            teams = [team for team in teams if (team.classification or "").casefold() == wanted]
        if not settings.fixture_mode and not teams:
            raise AppError(
                "UPSTREAM_EMPTY",
                "No usable teams were left after validation and the classification filter.",
                502,
                {"season": season, "classification": classification},
            )
        written = catalog._replace_teams(season, teams)
        catalog._success(
            resource="teams",
            season=season,
            team_id=None,
            records_written=written,
            http_status=None if result is None else result.http_status,
            rate_limit_remaining=None if result is None else result.rate_limit_remaining,
            started=started,
        )
    except AppError as exc:
        catalog.db.rollback()
        catalog._failure(resource="teams", season=season, team_id=None, error=exc, started=started)
        return _error_report("teams", exc)
    return _ok_report("teams", written, result)


def _load_games(catalog, settings, client, season, classification, force, calls) -> ResourceReport:
    if not force and catalog._fresh_refresh("games", season, None) is not None:
        return ResourceReport(resource="games", status="skipped", detail="Fresh cache.")
    started = time.perf_counter()
    try:
        payload, result = _games_payload(settings, client, season, classification, calls)
        games, _skipped = normalize_games(payload)
        if settings.fixture_mode:
            games = [game.model_copy(update={"season": season}) for game in games]
        else:
            games = [game for game in games if game.season == season]
        written = catalog.replace_games(season, games)
        catalog._success(
            resource="games",
            season=season,
            team_id=None,
            records_written=written,
            http_status=None if result is None else result.http_status,
            rate_limit_remaining=None if result is None else result.rate_limit_remaining,
            started=started,
        )
    except AppError as exc:
        catalog.db.rollback()
        catalog._failure(resource="games", season=season, team_id=None, error=exc, started=started)
        return _error_report("games", exc)
    return _ok_report("games", written, result)


def _load_stats(catalog, settings, client, season, classification, force, calls) -> ResourceReport:
    if not force and catalog._fresh_refresh("season_stats", season, None) is not None:
        return ResourceReport(resource="season_stats", status="skipped", detail="Fresh cache.")
    started = time.perf_counter()
    try:
        payload, result = _stats_payload(settings, client, season, classification, calls)
        stats, _skipped = normalize_stats(payload)
        if settings.fixture_mode:
            stats = [stat.model_copy(update={"season": season}) for stat in stats]
        grouped: dict[str, list] = {}
        for stat in stats:
            if stat.season != season:
                continue
            grouped.setdefault(stat.team.casefold(), []).append(stat)
        written = 0
        http_status = None if result is None else result.http_status
        remaining = None if result is None else result.rate_limit_remaining
        for team in catalog.teams_for_season(season):
            rows = grouped.get(team.school.casefold(), [])
            count = catalog._replace_stats(team, season, rows)
            written += count
            catalog._success(
                resource="team_season_stats",
                season=season,
                team_id=team.id,
                records_written=count,
                http_status=http_status,
                rate_limit_remaining=remaining,
                started=started,
            )
        catalog._success(
            resource="season_stats",
            season=season,
            team_id=None,
            records_written=written,
            http_status=http_status,
            rate_limit_remaining=remaining,
            started=started,
        )
    except AppError as exc:
        catalog.db.rollback()
        catalog._failure(resource="season_stats", season=season, team_id=None, error=exc, started=started)
        return _error_report("season_stats", exc)
    return _ok_report("season_stats", written, result)


def _teams_payload(settings: Settings, client: CfbdClient, season: int, calls: dict) -> tuple[object, CfbdResult | None]:
    if settings.fixture_mode:
        return load_fixture_list("teams.json", "teams"), None
    calls["n"] += 1
    result = client.fetch_teams(season)
    return result.payload, result


def _games_payload(
    settings: Settings,
    client: CfbdClient,
    season: int,
    classification: str,
    calls: dict,
) -> tuple[object, CfbdResult | None]:
    if settings.fixture_mode:
        return load_fixture_list("games.json", "games"), None
    calls["n"] += 1
    result = client.fetch_games(season, classification or None)
    return result.payload, result


def _stats_payload(
    settings: Settings,
    client: CfbdClient,
    season: int,
    classification: str,
    calls: dict,
) -> tuple[object, CfbdResult | None]:
    if settings.fixture_mode:
        return load_fixture_list("team_season_stats.json", "stats"), None
    calls["n"] += 1
    result = client.fetch_season_stats(season, classification or None)
    return result.payload, result


def _ok_report(resource: str, written: int, result: CfbdResult | None) -> ResourceReport:
    return ResourceReport(
        resource=resource,
        status="success",
        records_written=written,
        http_status=None if result is None else result.http_status,
        rate_limit_remaining=None if result is None else result.rate_limit_remaining,
    )


def _error_report(resource: str, exc: AppError) -> ResourceReport:
    return ResourceReport(
        resource=resource,
        status="error",
        error_code=exc.code,
        detail=exc.message,
        http_status=exc.status_code,
    )


def _quota_stop(report: ResourceReport, minimum: int) -> bool:
    if report.status != "success" or report.rate_limit_remaining is None:
        return False
    try:
        remaining = int(float(report.rate_limit_remaining))
    except ValueError:
        return False
    return remaining < minimum


def _stop_after(report: IngestReport, pending: tuple[str, ...]) -> IngestReport:
    report.stopped_early = True
    for resource in pending:
        report.resources.append(
            ResourceReport(
                resource=resource,
                status="stopped",
                error_code="QUOTA_GUARD",
                detail="Remaining provider quota is below CFIP_INGEST_MIN_REMAINING.",
            )
        )
    return report


def _should_pause(report: ResourceReport) -> bool:
    return report.status == "success" and report.http_status is not None


def _pause(seconds: float, sleeper) -> None:
    if seconds > 0:
        sleeper(seconds)
