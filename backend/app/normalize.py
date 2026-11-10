"""Validate and reshape upstream team and stat payloads.

The output models are the only objects persisted. Extra upstream fields,
including logos and social handles, are dropped on purpose.
"""

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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
