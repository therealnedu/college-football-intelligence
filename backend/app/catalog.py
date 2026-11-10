"""Season team directory: fetch, normalize, cache, and read."""

import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.cfbd import CfbdClient, CfbdResult
from app.config import Settings
from app.errors import AppError
from app.fixtures_loader import load_fixture_list
from app.models import DataRefreshLog, DataSource, Season, Team, TeamSeason, TeamStatistic
from app.normalize import FIXTURE_LABEL, NormalizedStat, NormalizedTeam, normalize_stats, normalize_teams
from app.schemas import (
    Attribution,
    CacheInfo,
    RefreshStatusItem,
    RefreshStatusResponse,
    StatOut,
    TeamListResponse,
    TeamOut,
    TeamStatsResponse,
)

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()

FIXTURE_NOTICE = (
    "FIXTURE DATA. These records were written for tests and local UI review. "
    f"{FIXTURE_LABEL}. Do not cite them."
)
LIVE_STATEMENT = (
    "Data provided by CollegeFootballData.com. These figures are not official "
    "NCAA, conference, or school statistics. Team names identify the subjects "
    "of the figures; no trademark use is claimed."
)


class Catalog:
    def __init__(self, db: Session, settings: Settings, client: CfbdClient) -> None:
        self.db = db
        self.settings = settings
        self.client = client

    def list_teams(self, season: int) -> TeamListResponse:
        self._assert_season(season)
        with _lock(f"{self.settings.origin}:teams:{season}"):
            cached = self._cached_team_list(season)
            if cached is not None:
                return cached
            started = time.perf_counter()
            try:
                teams, result = self._load_teams(season)
                written = self._replace_teams(season, teams)
                fetched_at = self._success(
                    resource="teams",
                    season=season,
                    team_id=None,
                    records_written=written,
                    http_status=None if result is None else result.http_status,
                    rate_limit_remaining=None if result is None else result.rate_limit_remaining,
                    started=started,
                )
            except AppError as exc:
                self.db.rollback()
                self._failure(resource="teams", season=season, team_id=None, error=exc, started=started)
                raise
        return self._team_list_response(season, fetched_at, cache_hit=False)

    def team_stats(self, team_id: int, season: int) -> TeamStatsResponse:
        self._assert_season(season)
        team = self._team_for_active_source(team_id)
        if team is None:
            raise AppError("TEAM_NOT_FOUND", "No team with that id is stored for the active data source.", 404)
        with _lock(f"{self.settings.origin}:stats:{season}:{team.id}"):
            cached = self._cached_stats(team, season)
            if cached is not None:
                return cached
            started = time.perf_counter()
            try:
                stats, result = self._load_stats(season, team.school)
                written = self._replace_stats(team, season, stats)
                fetched_at = self._success(
                    resource="team_season_stats",
                    season=season,
                    team_id=team.id,
                    records_written=written,
                    http_status=None if result is None else result.http_status,
                    rate_limit_remaining=None if result is None else result.rate_limit_remaining,
                    started=started,
                )
            except AppError as exc:
                self.db.rollback()
                self._failure(
                    resource="team_season_stats",
                    season=season,
                    team_id=team.id,
                    error=exc,
                    started=started,
                )
                raise
        return self._stats_response(team, season, fetched_at, cache_hit=False)

    def refresh_status(self, limit: int) -> RefreshStatusResponse:
        rows = self.db.scalars(
            select(DataRefreshLog).order_by(DataRefreshLog.started_at.desc()).limit(limit)
        ).all()
        return RefreshStatusResponse(
            refreshes=[
                RefreshStatusItem(
                    id=row.id,
                    resource=row.resource,
                    season=row.season_year,
                    teamId=row.team_id,
                    status=row.status,
                    origin=row.origin,  # type: ignore[arg-type]
                    httpStatus=row.http_status,
                    recordsWritten=row.records_written,
                    durationMs=row.duration_ms,
                    errorCode=row.error_code,
                    errorMessage=row.error_message,
                    rateLimitRemaining=row.rate_limit_remaining,
                    startedAt=_as_utc(row.started_at),
                    finishedAt=None if row.finished_at is None else _as_utc(row.finished_at),
                )
                for row in rows
            ]
        )

    def _load_teams(self, season: int) -> tuple[list[NormalizedTeam], CfbdResult | None]:
        if self.settings.fixture_mode:
            payload = load_fixture_list("teams.json", "teams")
            teams, _skipped = normalize_teams(payload)
            return teams, None
        result = self.client.fetch_teams(season)
        teams, _skipped = normalize_teams(result.payload)
        if not teams:
            raise AppError(
                "UPSTREAM_EMPTY",
                "CollegeFootballData.com returned no usable teams for that season.",
                502,
                {"season": season},
            )
        return teams, result

    def _load_stats(self, season: int, school: str) -> tuple[list[NormalizedStat], CfbdResult | None]:
        if self.settings.fixture_mode:
            payload = load_fixture_list("team_season_stats.json", "stats")
            stats, _skipped = normalize_stats(payload)
            # Fixture rows are season-agnostic samples. Stamp the requested
            # season so the UI can be reviewed without pretending the file
            # holds a real season's totals.
            stamped = [
                stat.model_copy(update={"season": season})
                for stat in stats
                if stat.team.casefold() == school.casefold()
            ]
            return stamped, None
        result = self.client.fetch_team_season_stats(season, school)
        stats, _skipped = normalize_stats(result.payload)
        return stats, result

    def _replace_teams(self, season: int, teams: list[NormalizedTeam]) -> int:
        self._ensure_season(season)
        source = self._source()
        now = _utcnow()
        for item in teams:
            team = self.db.scalar(
                select(Team).where(Team.source_id == source.id, Team.external_id == item.external_id)
            )
            if team is None:
                team = Team(
                    source_id=source.id,
                    external_id=item.external_id,
                    school=item.school,
                    mascot=item.mascot,
                    abbreviation=item.abbreviation,
                    color=item.color,
                    alternate_color=item.alternate_color,
                    fetched_at=now,
                )
                self.db.add(team)
                self.db.flush()
            else:
                team.school = item.school
                team.mascot = item.mascot
                team.abbreviation = item.abbreviation
                team.color = item.color
                team.alternate_color = item.alternate_color
                team.fetched_at = now
            affiliation = self.db.scalar(
                select(TeamSeason).where(
                    TeamSeason.team_id == team.id,
                    TeamSeason.season_year == season,
                    TeamSeason.origin == self.settings.origin,
                )
            )
            if affiliation is None:
                self.db.add(
                    TeamSeason(
                        team_id=team.id,
                        season_year=season,
                        conference=item.conference,
                        division=item.division,
                        classification=item.classification,
                        origin=self.settings.origin,
                        source_id=source.id,
                        fetched_at=now,
                    )
                )
            else:
                affiliation.conference = item.conference
                affiliation.division = item.division
                affiliation.classification = item.classification
                affiliation.fetched_at = now
        return len(teams)

    def _replace_stats(self, team: Team, season: int, stats: list[NormalizedStat]) -> int:
        self._ensure_season(season)
        source = self._source()
        now = _utcnow()
        self.db.execute(
            delete(TeamStatistic).where(
                TeamStatistic.team_id == team.id,
                TeamStatistic.season_year == season,
                TeamStatistic.origin == self.settings.origin,
            )
        )
        kept: list[NormalizedStat] = []
        for stat in stats:
            if stat.season != season or stat.team.casefold() != team.school.casefold():
                continue
            kept.append(stat)
            self.db.add(
                TeamStatistic(
                    team_id=team.id,
                    season_year=season,
                    stat_name=stat.stat_name,
                    stat_value_numeric=stat.value_numeric,
                    stat_value_text=stat.value_text,
                    conference=stat.conference,
                    origin=self.settings.origin,
                    source_id=source.id,
                    fetched_at=now,
                )
            )
        return len(kept)

    def _cached_team_list(self, season: int) -> TeamListResponse | None:
        refresh = self._fresh_refresh("teams", season, None)
        if refresh is None or refresh.finished_at is None:
            return None
        if not self._has_affiliations(season):
            return None
        return self._team_list_response(season, _as_utc(refresh.finished_at), cache_hit=True)

    def _cached_stats(self, team: Team, season: int) -> TeamStatsResponse | None:
        refresh = self._fresh_refresh("team_season_stats", season, team.id)
        if refresh is None or refresh.finished_at is None:
            return None
        return self._stats_response(team, season, _as_utc(refresh.finished_at), cache_hit=True)

    def _fresh_refresh(self, resource: str, season: int, team_id: int | None) -> DataRefreshLog | None:
        team_clause = (
            DataRefreshLog.team_id.is_(None) if team_id is None else DataRefreshLog.team_id == team_id
        )
        row = self.db.scalar(
            select(DataRefreshLog)
            .where(
                DataRefreshLog.resource == resource,
                DataRefreshLog.season_year == season,
                DataRefreshLog.status == "success",
                DataRefreshLog.origin == self.settings.origin,
                team_clause,
            )
            .order_by(DataRefreshLog.finished_at.desc())
            .limit(1)
        )
        if row is None or row.finished_at is None:
            return None
        age = _utcnow() - _as_utc(row.finished_at)
        if age > timedelta(seconds=self.settings.cfbd_cache_ttl_seconds):
            return None
        return row

    def _has_affiliations(self, season: int) -> bool:
        source = self._source()
        row = self.db.scalar(
            select(TeamSeason.id)
            .join(Team, Team.id == TeamSeason.team_id)
            .where(
                Team.source_id == source.id,
                TeamSeason.season_year == season,
                TeamSeason.origin == self.settings.origin,
            )
            .limit(1)
        )
        return row is not None

    def _team_for_active_source(self, team_id: int) -> Team | None:
        source = self._source()
        return self.db.scalar(select(Team).where(Team.id == team_id, Team.source_id == source.id))

    def _team_list_response(self, season: int, fetched_at: datetime, cache_hit: bool) -> TeamListResponse:
        source = self._source()
        rows = self.db.execute(
            select(Team, TeamSeason)
            .join(TeamSeason, TeamSeason.team_id == Team.id)
            .where(
                Team.source_id == source.id,
                TeamSeason.season_year == season,
                TeamSeason.origin == self.settings.origin,
            )
            .order_by(Team.school.asc())
        ).all()
        teams = [_team_out(team, affiliation) for team, affiliation in rows]
        return TeamListResponse(
            season=season,
            teams=teams,
            attribution=self._attribution(fetched_at),
            cache=CacheInfo(hit=cache_hit, ttlSeconds=self.settings.cfbd_cache_ttl_seconds, fetchedAt=fetched_at),
        )

    def _stats_response(self, team: Team, season: int, fetched_at: datetime, cache_hit: bool) -> TeamStatsResponse:
        affiliation = self.db.scalar(
            select(TeamSeason).where(
                TeamSeason.team_id == team.id,
                TeamSeason.season_year == season,
                TeamSeason.origin == self.settings.origin,
            )
        )
        stat_rows = self.db.scalars(
            select(TeamStatistic)
            .where(
                TeamStatistic.team_id == team.id,
                TeamStatistic.season_year == season,
                TeamStatistic.origin == self.settings.origin,
            )
            .order_by(TeamStatistic.stat_name.asc())
        ).all()
        return TeamStatsResponse(
            team=_team_out(team, affiliation),
            season=season,
            stats=[_stat_out(row) for row in stat_rows],
            attribution=self._attribution(fetched_at),
            cache=CacheInfo(hit=cache_hit, ttlSeconds=self.settings.cfbd_cache_ttl_seconds, fetchedAt=fetched_at),
        )

    def _attribution(self, fetched_at: datetime) -> Attribution:
        if self.settings.fixture_mode:
            return Attribution(
                providerName="CFIP synthetic fixture",
                providerUrl=None,
                termsUrl=None,
                statement=FIXTURE_NOTICE,
                fetchedAt=fetched_at,
                dataMode="fixture",
                fixtureNotice=FIXTURE_NOTICE,
            )
        return Attribution(
            providerName="CollegeFootballData.com",
            providerUrl="https://collegefootballdata.com",
            termsUrl="https://collegefootballdata.com/terms",
            statement=LIVE_STATEMENT,
            fetchedAt=fetched_at,
            dataMode="live",
            fixtureNotice=None,
        )

    def _success(
        self,
        resource: str,
        season: int,
        team_id: int | None,
        records_written: int,
        http_status: int | None,
        rate_limit_remaining: str | None,
        started: float,
    ) -> datetime:
        elapsed = _elapsed_ms(started)
        finished = _utcnow()
        source = self._source()
        self.db.add(
            DataRefreshLog(
                source_id=source.id,
                resource=resource,
                season_year=season,
                team_id=team_id,
                status="success",
                origin=self.settings.origin,
                http_status=http_status,
                records_written=records_written,
                duration_ms=elapsed,
                rate_limit_remaining=rate_limit_remaining,
                started_at=finished - timedelta(milliseconds=elapsed),
                finished_at=finished,
            )
        )
        self.db.commit()
        return finished

    def _failure(
        self,
        resource: str,
        season: int,
        team_id: int | None,
        error: AppError,
        started: float,
    ) -> None:
        source = self.db.scalar(select(DataSource).where(DataSource.code == self.settings.source_code))
        self.db.add(
            DataRefreshLog(
                source_id=None if source is None else source.id,
                resource=resource,
                season_year=season,
                team_id=team_id,
                status="error",
                origin=self.settings.origin,
                http_status=error.status_code,
                records_written=0,
                duration_ms=_elapsed_ms(started),
                error_code=error.code,
                error_message=error.message,
                rate_limit_remaining=_detail_str(error.details.get("rateLimitRemaining")),
                started_at=_utcnow(),
                finished_at=_utcnow(),
            )
        )
        self.db.commit()

    def _source(self) -> DataSource:
        source = self.db.scalar(select(DataSource).where(DataSource.code == self.settings.source_code))
        if source is None:
            raise AppError("SOURCE_NOT_SEEDED", "The data source reference row is missing.", 500)
        return source

    def _ensure_season(self, year: int) -> None:
        if self.db.get(Season, year) is None:
            self.db.add(Season(year=year))
            self.db.flush()

    def _assert_season(self, season: int) -> None:
        if season < self.settings.cfip_min_season or season > self.settings.max_season:
            raise AppError(
                "SEASON_OUT_OF_RANGE",
                (
                    f"Season must be from {self.settings.cfip_min_season} through "
                    f"{self.settings.max_season}."
                ),
                422,
                {
                    "minSeason": self.settings.cfip_min_season,
                    "maxSeason": self.settings.max_season,
                    "coverage": (
                        "CollegeFootballData.com documents season team statistics "
                        "from 2004 through the present. The current season can be incomplete."
                    ),
                },
            )


def _team_out(team: Team, affiliation: TeamSeason | None) -> TeamOut:
    return TeamOut(
        id=team.id,
        externalId=team.external_id,
        school=team.school,
        mascot=team.mascot,
        abbreviation=team.abbreviation,
        conference=None if affiliation is None else affiliation.conference,
        division=None if affiliation is None else affiliation.division,
        classification=None if affiliation is None else affiliation.classification,
        color=team.color,
        alternateColor=team.alternate_color,
    )


def _stat_out(row: TeamStatistic) -> StatOut:
    numeric = row.stat_value_numeric
    if isinstance(numeric, Decimal):
        value = float(numeric)
    elif numeric is None:
        value = None
    else:
        value = float(numeric)
    return StatOut(
        name=row.stat_name,
        valueNumeric=value,
        valueText=row.stat_value_text,
        conference=row.conference,
    )


def _lock(key: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _detail_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
