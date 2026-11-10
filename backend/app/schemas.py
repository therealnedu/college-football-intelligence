"""Public API models. These are CFIP's contract, not the upstream payload."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


class Attribution(BaseModel):
    providerName: str
    providerUrl: str | None = None
    termsUrl: str | None = None
    statement: str
    fetchedAt: datetime
    dataMode: Literal["live", "fixture"]
    fixtureNotice: str | None = None


class CacheInfo(BaseModel):
    hit: bool
    ttlSeconds: int
    fetchedAt: datetime


class TeamOut(BaseModel):
    id: int
    externalId: int
    school: str
    mascot: str | None = None
    abbreviation: str | None = None
    conference: str | None = None
    division: str | None = None
    classification: str | None = None
    color: str | None = None
    alternateColor: str | None = None


class TeamListResponse(BaseModel):
    season: int
    teams: list[TeamOut]
    attribution: Attribution
    cache: CacheInfo


class StatOut(BaseModel):
    name: str
    valueNumeric: float | None = None
    valueText: str
    conference: str | None = None


class TeamStatsResponse(BaseModel):
    team: TeamOut
    season: int
    stats: list[StatOut]
    attribution: Attribution
    cache: CacheInfo


class SeasonBounds(BaseModel):
    minSeason: int
    maxSeason: int
    defaultSeason: int
    coverageNote: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    phase: int
    dataMode: Literal["live", "fixture"]
    cfbdConfigured: bool
    database: Literal["ok"]


class RefreshStatusItem(BaseModel):
    id: int
    resource: str
    season: int | None = None
    teamId: int | None = None
    status: str
    origin: Literal["live", "fixture"]
    httpStatus: int | None = None
    recordsWritten: int
    durationMs: int | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    rateLimitRemaining: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None


class RefreshStatusResponse(BaseModel):
    refreshes: list[RefreshStatusItem]
