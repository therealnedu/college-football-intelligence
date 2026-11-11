"""Runtime configuration. Secrets come from the environment, never from source."""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cfbd_api_key: str = ""
    cfbd_base_url: str = "https://api.collegefootballdata.com"
    cfbd_timeout_seconds: float = 20.0
    cfbd_max_retries: int = 3
    cfbd_backoff_seconds: float = 0.5
    cfbd_cache_ttl_seconds: int = 86_400
    database_url: str = "sqlite:///./data/cfip.db"
    cfip_data_mode: str = "live"
    cfip_cors_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    cfip_log_level: str = "INFO"
    cfip_auto_migrate: bool = True
    cfip_min_season: int = 2004
    cfip_max_season: int | None = Field(default=None)
    # Live ingest keeps this classification. Fixture ingest ignores it,
    # because the synthetic schools are not FBS programs.
    cfip_ingest_classification: str = "fbs"
    cfip_ingest_pause_seconds: float = 1.0
    cfip_ingest_min_remaining: int = 25

    @property
    def fixture_mode(self) -> bool:
        return self.cfip_data_mode.strip().lower() == "fixture"

    @property
    def origin(self) -> str:
        return "fixture" if self.fixture_mode else "live"

    @property
    def source_code(self) -> str:
        return "cfip_fixture" if self.fixture_mode else "cfbd"

    @property
    def max_season(self) -> int:
        if self.cfip_max_season is not None:
            return self.cfip_max_season
        return datetime.now(timezone.utc).year

    @property
    def default_season(self) -> int:
        """Previous calendar year.

        The in-progress season is the current calendar year during the fall.
        Defaulting to the previous year avoids presenting a partial season as
        the landing choice. It is not a claim that the previous season is complete.
        """

        proposed = self.max_season - 1
        return min(self.max_season, max(self.cfip_min_season, proposed))

    @property
    def cors_origins(self) -> list[str]:
        raw = [item.strip() for item in self.cfip_cors_origins.split(",") if item.strip()]
        return raw or ["http://127.0.0.1:43123"]

    @property
    def allow_all_origins(self) -> bool:
        return self.cors_origins == ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
