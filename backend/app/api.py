"""HTTP routes for phase 1."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.catalog import Catalog
from app.cfbd import CfbdClient
from app.config import get_settings
from app.db import get_db
from app.schemas import (
    GamesResponse,
    HealthResponse,
    RefreshStatusResponse,
    SeasonBounds,
    TeamListResponse,
    TeamStatsResponse,
)

router = APIRouter()

COVERAGE_NOTE = (
    "CollegeFootballData.com documents team and player box-score statistics, "
    "including season team stats, for 2004 through the present. Coverage was "
    "last checked on their data-availability page on 2026-11-10. A season inside "
    "that range can still be incomplete, especially the season currently being "
    "played. The default season is the previous calendar year so the landing "
    "choice is not the in-progress season. That is a calendar rule, not a claim "
    "that every figure in the default season is complete."
)


def get_client() -> CfbdClient:
    return CfbdClient(get_settings())


def get_catalog(
    db: Session = Depends(get_db),
    client: CfbdClient = Depends(get_client),
) -> Catalog:
    return Catalog(db=db, settings=get_settings(), client=client)


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="cfip-api",
        phase=1,
        dataMode="fixture" if settings.fixture_mode else "live",
        cfbdConfigured=bool(settings.cfbd_api_key.strip()),
        database="ok",
    )


@router.get("/seasons", response_model=SeasonBounds)
def seasons() -> SeasonBounds:
    settings = get_settings()
    return SeasonBounds(
        minSeason=settings.cfip_min_season,
        maxSeason=settings.max_season,
        defaultSeason=settings.default_season,
        coverageNote=COVERAGE_NOTE,
    )


@router.get("/teams", response_model=TeamListResponse)
def teams(
    season: int = Query(..., description="Season year, from 2004 through the current calendar year."),
    catalog: Catalog = Depends(get_catalog),
) -> TeamListResponse:
    return catalog.list_teams(season)


@router.get("/games", response_model=GamesResponse)
def games(
    season: int = Query(..., description="Season year."),
    teamId: int | None = Query(default=None, description="Limit to games involving this CFIP team id."),
    catalog: Catalog = Depends(get_catalog),
) -> GamesResponse:
    return catalog.list_games(season, teamId)


@router.get("/teams/{team_id}/stats", response_model=TeamStatsResponse)
def team_stats(
    team_id: int,
    season: int = Query(..., description="Season year."),
    catalog: Catalog = Depends(get_catalog),
) -> TeamStatsResponse:
    return catalog.team_stats(team_id, season)


@router.get("/refresh-status", response_model=RefreshStatusResponse)
def refresh_status(
    limit: int = Query(20, ge=1, le=100),
    catalog: Catalog = Depends(get_catalog),
) -> RefreshStatusResponse:
    return catalog.refresh_status(limit)
