"""Write the public snapshot the static site reads.

The file uses CFIP's response fields. It is not a provider payload. Betting
keys, logos, and raw stat names from the upstream document are refused before
the file is written.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import Catalog, _stat_out, _team_out
from app.cfbd import CfbdClient
from app.config import Settings
from app.errors import AppError
from app.models import Team, TeamSeason, TeamStatistic
from app.normalize import FIXTURE_LABEL
from app.pipeline import IngestReport
from app.schemas import Attribution, GameOut, SeasonBounds, StatOut, TeamOut

BANNED_KEYS = {
    "spread",
    "overunder",
    "over_under",
    "moneyline",
    "homemoneyline",
    "awaymoneyline",
    "logos",
    "twitter",
    "statvalue",
    "statname",
    "betting",
    "homelinescores",
    "awaylinescores",
    "lines",
}


class SnapshotResource(BaseModel):
    resource: str
    status: str
    recordsWritten: int


class SnapshotIngest(BaseModel):
    providerCalls: int
    stoppedEarly: bool
    note: str
    resources: list[SnapshotResource]


class SnapshotDocument(BaseModel):
    snapshotVersion: int = 1
    generatedAt: datetime
    season: int
    dataMode: str
    delivery: str = "snapshot"
    attribution: Attribution
    seasons: SeasonBounds
    teams: list[TeamOut]
    games: list[GameOut]
    statsByTeamId: dict[str, list[StatOut]]
    ingest: SnapshotIngest
    coverageNote: str = Field(
        default="",
        description="Duplicated onto seasons.coverageNote. Kept so a reader of the file sees it at the top.",
    )


def build_snapshot(db: Session, settings: Settings, season: int, report: IngestReport) -> dict:
    catalog = Catalog(db, settings, CfbdClient(settings))
    generated_at = datetime.now(timezone.utc)
    fetched_at = _latest_fetch(catalog, season) or generated_at
    attribution = catalog._attribution(fetched_at)
    source = catalog._source()
    directory = db.execute(
        select(Team, TeamSeason)
        .join(TeamSeason, TeamSeason.team_id == Team.id)
        .where(
            Team.source_id == source.id,
            TeamSeason.season_year == season,
            TeamSeason.origin == settings.origin,
        )
        .order_by(Team.school.asc())
    ).all()
    teams: list[TeamOut] = []
    stats_by_team: dict[str, list[StatOut]] = {}
    for team, affiliation in directory:
        teams.append(_team_out(team, affiliation))
        rows = db.scalars(
            select(TeamStatistic)
            .where(
                TeamStatistic.team_id == team.id,
                TeamStatistic.season_year == season,
                TeamStatistic.origin == settings.origin,
            )
            .order_by(TeamStatistic.stat_name.asc())
        ).all()
        stats_by_team[str(team.id)] = [_stat_out(row) for row in rows]
    games_response = catalog._games_response(season, fetched_at, True, None)
    note = _note(report)
    if settings.fixture_mode:
        coverage = (
            "This public page includes one season of synthetic fixture data so the site can be "
            "opened without a provider key. NOT REAL COLLEGE FOOTBALL STATISTICS. "
            "It is not a history from 2004."
        )
    else:
        coverage = (
            f"This public page is a static snapshot of the {season} season, "
            f"classification {settings.cfip_ingest_classification or 'unfiltered'}. "
            "CollegeFootballData.com documents season team statistics from 2004 through the "
            "present. The current season can be incomplete. Opening this page does not call the provider."
        )
    document = SnapshotDocument(
        generatedAt=generated_at,
        season=season,
        dataMode="fixture" if settings.fixture_mode else "live",
        attribution=attribution,
        seasons=SeasonBounds(
            minSeason=season,
            maxSeason=season,
            defaultSeason=season,
            coverageNote=coverage,
        ),
        teams=teams,
        games=list(games_response.games),
        statsByTeamId=stats_by_team,
        ingest=SnapshotIngest(
            providerCalls=report.provider_calls,
            stoppedEarly=report.stopped_early,
            note=note,
            resources=[
                SnapshotResource(
                    resource=item.resource,
                    status=item.status,
                    recordsWritten=item.records_written,
                )
                for item in report.resources
            ],
        ),
        coverageNote=coverage,
    )
    payload = document.model_dump(mode="json")
    _assert_safe(payload)
    return payload


def write_snapshot(path: Path, payload: dict) -> None:
    _assert_safe(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(path)


def _latest_fetch(catalog: Catalog, season: int) -> datetime | None:
    latest: datetime | None = None
    for resource, team_id in (("teams", None), ("games", None), ("season_stats", None)):
        row = catalog._fresh_refresh(resource, season, team_id)
        # A forced rebuild is still "fresh" for the default TTL. If the row is
        # older than the TTL, fall through and use generatedAt.
        if row is None or row.finished_at is None:
            continue
        finished = row.finished_at
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        if latest is None or finished > latest:
            latest = finished
    return latest


def _note(report: IngestReport) -> str:
    if report.data_mode == "fixture":
        return (
            "Built from CFIP synthetic fixtures. No CollegeFootballData.com call was made. "
            f"{FIXTURE_LABEL}."
        )
    if report.stopped_early:
        return (
            "Partial live load. Ingest stopped before every resource finished because the "
            "remaining monthly quota was below the guard. Figures that are present were stored "
            "from CollegeFootballData.com. Missing games or stats were not filled in."
        )
    return (
        "Built from CollegeFootballData.com for one season. This file is a static display copy, "
        "not a live feed and not a raw mirror of the provider."
    )


def _assert_safe(payload: dict) -> None:
    _reject_banned_keys(payload)
    attribution = payload.get("attribution") or {}
    statement = str(attribution.get("statement") or "")
    notice = str(attribution.get("fixtureNotice") or "")
    if payload.get("dataMode") == "fixture":
        if FIXTURE_LABEL not in statement and FIXTURE_LABEL not in notice:
            raise AppError(
                "SNAPSHOT_UNLABELED",
                "Refusing to write a fixture snapshot that is missing the synthetic-data label.",
                500,
            )
    elif FIXTURE_LABEL in statement or FIXTURE_LABEL in notice:
        raise AppError(
            "SNAPSHOT_MISLABELED",
            "Refusing to write a live snapshot that carries the fixture label.",
            500,
        )


def _reject_banned_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in BANNED_KEYS:
                raise AppError(
                    "SNAPSHOT_UNSAFE",
                    f"Refusing to write a snapshot that contains the field {key}.",
                    500,
                )
            _reject_banned_keys(item)
    elif isinstance(value, list):
        for item in value:
            _reject_banned_keys(item)
