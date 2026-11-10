"""Relational schema for CFIP.

Phase 1 writes data_sources, seasons, teams, team_seasons, team_statistics,
and data_refresh_logs. The other tables exist so later phases have a stable
contract; this phase does not put rows in them.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    terms_url: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    teams: Mapped[list["Team"]] = relationship(back_populates="source")


class Season(Base):
    __tablename__ = "seasons"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_teams_source_external"),
        Index("ix_teams_school", "school"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    school: Mapped[str] = mapped_column(String(200), nullable=False)
    mascot: Mapped[str | None] = mapped_column(String(200))
    abbreviation: Mapped[str | None] = mapped_column(String(32))
    color: Mapped[str | None] = mapped_column(String(32))
    alternate_color: Mapped[str | None] = mapped_column(String(32))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped[DataSource] = relationship(back_populates="teams")
    seasons: Mapped[list["TeamSeason"]] = relationship(back_populates="team")
    statistics: Mapped[list["TeamStatistic"]] = relationship(back_populates="team")


class TeamSeason(Base):
    """Conference and division are properties of a team in a season, not of the team forever."""

    __tablename__ = "team_seasons"
    __table_args__ = (
        UniqueConstraint("team_id", "season_year", "origin", name="uq_team_seasons_identity"),
        Index("ix_team_seasons_season_origin", "season_year", "origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.year"), nullable=False)
    conference: Mapped[str | None] = mapped_column(String(120))
    division: Mapped[str | None] = mapped_column(String(64))
    classification: Mapped[str | None] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    team: Mapped[Team] = relationship(back_populates="seasons")


class Game(Base):
    """Created for later phases. Phase 1 does not ingest games."""

    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_games_source_external"),
        Index("ix_games_season_week", "season_year", "week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.year"), nullable=False)
    week: Mapped[int | None] = mapped_column(Integer)
    season_type: Mapped[str | None] = mapped_column(String(32))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    home_points: Mapped[int | None] = mapped_column(Integer)
    away_points: Mapped[int | None] = mapped_column(Integer)
    neutral_site: Mapped[bool | None] = mapped_column(Boolean)
    venue: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(32))
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TeamStatistic(Base):
    __tablename__ = "team_statistics"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "season_year",
            "stat_name",
            "origin",
            name="uq_team_statistics_identity",
        ),
        Index("ix_team_statistics_season_stat", "season_year", "stat_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.year"), nullable=False)
    stat_name: Mapped[str] = mapped_column(String(120), nullable=False)
    stat_value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(16, 4))
    stat_value_text: Mapped[str] = mapped_column(String(120), nullable=False)
    conference: Mapped[str | None] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    team: Mapped[Team] = relationship(back_populates="statistics")


class MatchupAnalysis(Base):
    """Phase 2 comparison record. Unused in phase 1."""

    __tablename__ = "matchup_analyses"
    __table_args__ = (
        UniqueConstraint(
            "season_year",
            "team_a_id",
            "team_b_id",
            name="uq_matchup_analyses_pair",
        ),
        CheckConstraint("team_a_id <> team_b_id", name="distinct_teams"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.year"), nullable=False)
    team_a_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    team_b_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class ScoutingReport(Base):
    """Phase 3 grounded narrative. Unused in phase 1."""

    __tablename__ = "scouting_reports"
    __table_args__ = (Index("ix_scouting_reports_team_season", "team_id", "season_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.year"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class AIExecutionLog(Base):
    """Phase 4 tool-calling audit. Unused in phase 1.

    input_hash is a fingerprint, not the prompt. Do not store secrets or raw
    provider payloads here.
    """

    __tablename__ = "ai_execution_logs"
    __table_args__ = (Index("ix_ai_execution_logs_started", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(128))
    output_validated: Mapped[bool | None] = mapped_column(Boolean)
    error_message: Mapped[str | None] = mapped_column(Text)


class DataRefreshLog(Base):
    """One row per attempt to refresh a resource from its source.

    Cache hits are not rows. They are reported on the API response so this
    table stays a refresh log rather than an access log.
    """

    __tablename__ = "data_refresh_logs"
    __table_args__ = (
        Index(
            "ix_data_refresh_logs_lookup",
            "resource",
            "season_year",
            "team_id",
            "origin",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    season_year: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    records_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    rate_limit_remaining: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
