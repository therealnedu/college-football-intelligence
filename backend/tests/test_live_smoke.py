"""Live smoke test.

Skipped unless CFBD_API_KEY is set. When it runs, it spends two
CollegeFootballData.com calls (one team list, one team-season stat request)
and then confirms the second read of each is served from SQLite.

It asserts the response contract only. It does not assert statistic values,
and it does not write the provider payload into the repository.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.mark.live
def test_live_team_stats_contract(tmp_path, monkeypatch):
    api_key = os.environ.get("CFBD_API_KEY", "").strip()
    if not api_key:
        pytest.skip("CFBD_API_KEY is not set. Live retrieval was not executed.")

    database = tmp_path / "live.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("CFIP_DATA_MODE", "live")
    monkeypatch.setenv("CFBD_API_KEY", api_key)
    monkeypatch.setenv("CFIP_AUTO_MIGRATE", "true")
    monkeypatch.setenv("CFBD_CACHE_TTL_SECONDS", "86400")

    from app.config import get_settings
    from app.db import dispose_engine

    get_settings.cache_clear()
    dispose_engine()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        season = 2024
        first = client.get("/teams", params={"season": season})
        assert first.status_code == 200, first.text[:300]
        body = first.json()
        assert body["cache"]["hit"] is False
        assert body["attribution"]["dataMode"] == "live"
        assert body["attribution"]["providerName"] == "CollegeFootballData.com"
        assert body["teams"], "provider returned no teams for the smoke season"
        for team in body["teams"]:
            assert isinstance(team["externalId"], int)
            assert team["school"]

        second = client.get("/teams", params={"season": season})
        assert second.status_code == 200
        assert second.json()["cache"]["hit"] is True

        team_id = body["teams"][0]["id"]
        stats = client.get(f"/teams/{team_id}/stats", params={"season": season})
        assert stats.status_code == 200, stats.text[:300]
        stats_body = stats.json()
        assert stats_body["cache"]["hit"] is False
        assert stats_body["attribution"]["dataMode"] == "live"
        assert isinstance(stats_body["stats"], list)
        for stat in stats_body["stats"]:
            assert stat["name"]
            assert isinstance(stat["valueText"], str)

        stats_again = client.get(f"/teams/{team_id}/stats", params={"season": season})
        assert stats_again.status_code == 200
        assert stats_again.json()["cache"]["hit"] is True

    dispose_engine()
    get_settings.cache_clear()
