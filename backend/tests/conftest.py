import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def fixture_client(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, mode="fixture", api_key="")
    try:
        yield client
    finally:
        client.cleanup()


@pytest.fixture
def unconfigured_live_client(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, mode="live", api_key="")
    try:
        yield client
    finally:
        client.cleanup()


def _client(tmp_path, monkeypatch, mode: str, api_key: str) -> TestClient:
    database = tmp_path / "cfip.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("CFIP_DATA_MODE", mode)
    monkeypatch.setenv("CFBD_API_KEY", api_key)
    monkeypatch.setenv("CFIP_AUTO_MIGRATE", "true")
    monkeypatch.setenv("CFBD_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("CFBD_CACHE_TTL_SECONDS", "86400")

    from app.config import get_settings
    from app.db import dispose_engine

    get_settings.cache_clear()
    dispose_engine()

    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    client.__enter__()

    def _cleanup() -> None:
        client.__exit__(None, None, None)
        dispose_engine()
        get_settings.cache_clear()

    client.cleanup = _cleanup  # type: ignore[attr-defined]
    return client
