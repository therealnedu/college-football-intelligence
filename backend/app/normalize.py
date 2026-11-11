"""Validate and reshape upstream team, game, and stat payloads.

The output models are the only objects persisted. Extra upstream fields,
including logos, social handles, and betting objects, are dropped on purpose.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.errors import AppError

FIXTURE_LABEL = "NOT REAL COLLEGE FOOTBALL STATISTICS"


class NormalizedTeam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: int
    school: str
    mascot: str | None = None
    abbreviation: str | None = None
    conference: str | None = None
    division: str | None = None
    classification: str | None = None
    color: str | None = None
    alternate_color: str | None = None


class NormalizedStat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season: int
    team: str
    conference: str | None = None
    stat_name: str
    value_numeric: Decimal | None = None
    value_text: str


class NormalizedGame(BaseModel):
    """A game reduced to identity, participants, and the stored score.

    `home_points` and `away_points` are null when the provider did not send a
    score. They are never coerced to zero.
    """

    model_config = ConfigDict(extra="forbid")

    external_id: int
    season: int
    week: int | None = None
    season_type: str | None = None
    start_at: datetime | None = None
    home_external_id: int | None = None
    away_external_id: int | None = None
    home_school: str
    away_school: str
    home_points: int | None = None
    away_points: int | None = None
    neutral_site: bool | None = None
    venue: str | None = None
    status: str | None = None


class _TeamRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int
    school: str
    mascot: str | None = None
    abbreviation: str | None = None
    conference: str | None = None
    division: str | None = None
    classification: str | None = None
    color: str | None = None
    alternate_color: str | None = Field(default=None, alias="alternateColor")

    @field_validator("school")
    @classmethod
    def school_present(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("school is blank")
        return cleaned


class _StatRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    season: int
    team: str
    conference: str | None = None
    stat_name: str = Field(alias="statName")
    stat_value: object | None = Field(default=None, alias="statValue")

    @field_validator("team", "stat_name")
    @classmethod
    def required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("required text is blank")
        return cleaned


def parse_stat_value(value: object) -> tuple[Decimal | None, str]:
    """Return a numeric value only when the token is a finite decimal.

    Commas are removed before parsing so '1,234' can be stored as 1234.
    Clock strings such as '12:34' stay text. Booleans are not numbers.
    """

    if value is None:
        return None, ""
    if isinstance(value, bool):
        return None, "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            return None, str(value)
        if not number.is_finite():
            return None, str(value)
        return number, format(number, "f")
    text = str(value).strip()
    if text == "":
        return None, ""
    numeric_token = text.replace(",", "")
    try:
        number = Decimal(numeric_token)
    except InvalidOperation:
        return None, text
    if not number.is_finite():
        return None, text
    return number, text


def normalize_teams(payload: object) -> tuple[list[NormalizedTeam], int]:
    records = _require_list(payload, "teams")
    teams: list[NormalizedTeam] = []
    skipped = 0
    for record in records:
        try:
            parsed = _TeamRecord.model_validate(record)
        except ValidationError:
            skipped += 1
            continue
        teams.append(
            NormalizedTeam(
                external_id=parsed.id,
                school=parsed.school,
                mascot=_blank_to_none(parsed.mascot),
                abbreviation=_blank_to_none(parsed.abbreviation),
                conference=_blank_to_none(parsed.conference),
                division=_blank_to_none(parsed.division),
                classification=_blank_to_none(parsed.classification),
                color=_blank_to_none(parsed.color),
                alternate_color=_blank_to_none(parsed.alternate_color),
            )
        )
    if records and not teams:
        raise AppError(
            "UPSTREAM_INVALID",
            "The team payload did not contain any usable team records.",
            502,
            {"skipped": skipped},
        )
    return teams, skipped


class _GameRecord(BaseModel):
    """Flat game shape, plus a nested homeTeam/awayTeam object if one arrives.

    Betting, line scores, elo, and win probability are not fields here, so
    they cannot be copied onto the normalized game.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int
    season: int
    week: int | None = None
    season_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("seasonType", "season_type"),
    )
    start_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("startDate", "start_date"),
    )
    completed: bool | None = None
    status: str | None = None
    neutral_site: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("neutralSite", "neutral_site"),
    )
    venue: str | None = None
    home_id: int | None = Field(default=None, validation_alias=AliasChoices("homeId", "home_id"))
    away_id: int | None = Field(default=None, validation_alias=AliasChoices("awayId", "away_id"))
    home_team: str | None = Field(default=None, validation_alias=AliasChoices("homeTeam", "home_team"))
    away_team: str | None = Field(default=None, validation_alias=AliasChoices("awayTeam", "away_team"))
    home_points: object | None = Field(
        default=None,
        validation_alias=AliasChoices("homePoints", "home_points"),
    )
    away_points: object | None = Field(
        default=None,
        validation_alias=AliasChoices("awayPoints", "away_points"),
    )

    @model_validator(mode="before")
    @classmethod
    def flatten_nested_sides(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        _flatten_side(data, "homeTeam", "home_team", "homeId", "home_id", "homePoints", "home_points")
        _flatten_side(data, "awayTeam", "away_team", "awayId", "away_id", "awayPoints", "away_points")
        venue = data.get("venue")
        if isinstance(venue, dict):
            name = venue.get("name")
            data["venue"] = name if isinstance(name, str) else None
        return data

    @field_validator("venue", "home_team", "away_team", "season_type", "status", mode="before")
    @classmethod
    def text_or_none(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None


def normalize_games(payload: object) -> tuple[list[NormalizedGame], int]:
    records = _require_list(payload, "games")
    games: list[NormalizedGame] = []
    skipped = 0
    for record in records:
        try:
            parsed = _GameRecord.model_validate(record)
        except ValidationError:
            skipped += 1
            continue
        home = _blank_to_none(parsed.home_team)
        away = _blank_to_none(parsed.away_team)
        if home is None or away is None:
            skipped += 1
            continue
        games.append(
            NormalizedGame(
                external_id=parsed.id,
                season=parsed.season,
                week=parsed.week,
                season_type=_blank_to_none(parsed.season_type),
                start_at=_parse_start(parsed.start_date),
                home_external_id=parsed.home_id,
                away_external_id=parsed.away_id,
                home_school=home,
                away_school=away,
                home_points=_parse_points(parsed.home_points),
                away_points=_parse_points(parsed.away_points),
                neutral_site=parsed.neutral_site,
                venue=_blank_to_none(parsed.venue),
                status=_game_status(parsed.completed, parsed.status),
            )
        )
    if records and not games:
        raise AppError(
            "UPSTREAM_INVALID",
            "The games payload did not contain any usable game records.",
            502,
            {"skipped": skipped},
        )
    return games, skipped


def normalize_stats(payload: object) -> tuple[list[NormalizedStat], int]:
    records = _require_list(payload, "team season stats")
    stats: list[NormalizedStat] = []
    skipped = 0
    for record in records:
        try:
            parsed = _StatRecord.model_validate(record)
        except ValidationError:
            skipped += 1
            continue
        numeric, text = parse_stat_value(parsed.stat_value)
        stats.append(
            NormalizedStat(
                season=parsed.season,
                team=parsed.team,
                conference=_blank_to_none(parsed.conference),
                stat_name=parsed.stat_name,
                value_numeric=numeric,
                value_text=text,
            )
        )
    return stats, skipped


def _require_list(payload: object, label: str) -> list:
    if not isinstance(payload, list):
        raise AppError(
            "UPSTREAM_INVALID",
            f"The {label} payload was not a list.",
            502,
        )
    return payload


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _first(data: dict, *keys: str) -> object:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _flatten_side(
    data: dict,
    camel_team: str,
    snake_team: str,
    camel_id: str,
    snake_id: str,
    camel_points: str,
    snake_points: str,
) -> None:
    nested = data.get(camel_team)
    if not isinstance(nested, dict):
        nested = data.get(snake_team)
    if not isinstance(nested, dict):
        return
    school = nested.get("name") or nested.get("school") or nested.get("team")
    data[camel_team] = school
    if _first(data, camel_id, snake_id) is None and nested.get("id") is not None:
        data[camel_id] = nested.get("id")
    if _first(data, camel_points, snake_points) is None and "points" in nested:
        data[camel_points] = nested.get("points")


def _parse_points(value: object) -> int | None:
    """A score is a non-negative integer. Booleans and blanks stay null, not zero."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if not value.is_integer() or value < 0:
            return None
        return int(value)
    if isinstance(value, str):
        token = value.strip()
        if token.isdigit():
            return int(token)
    return None


def _parse_start(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


_STATUS_ALLOWLIST = {
    "scheduled": "scheduled",
    "in_progress": "in_progress",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "postponed": "postponed",
    "final": "final",
    "completed": "final",
}


def _game_status(completed: bool | None, status: str | None) -> str:
    if completed is True:
        return "final"
    if completed is False:
        return "scheduled"
    if status is None:
        return "unknown"
    return _STATUS_ALLOWLIST.get(status.strip().lower(), "unknown")
