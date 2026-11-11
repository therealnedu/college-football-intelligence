import httpx

from app.cfbd import CfbdClient
from app.config import get_settings
from app.fixtures_loader import load_fixture_list


def test_health_and_season_bounds(fixture_client):
    health = fixture_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["dataMode"] == "fixture"
    assert health.json()["cfbdConfigured"] is False
    assert health.headers["X-Response-Time-Ms"]

    seasons = fixture_client.get("/seasons")
    body = seasons.json()
    assert body["minSeason"] == 2004
    assert body["defaultSeason"] == body["maxSeason"] - 1
    assert "2004" in body["coverageNote"]


def test_fixture_team_flow_is_labeled_and_cached(fixture_client):
    first = fixture_client.get("/teams", params={"season": 2025})
    assert first.status_code == 200
    payload = first.json()
    assert payload["cache"]["hit"] is False
    assert payload["attribution"]["dataMode"] == "fixture"
    assert payload["attribution"]["providerName"] == "CFIP synthetic fixture"
    assert "NOT REAL COLLEGE FOOTBALL STATISTICS" in payload["attribution"]["fixtureNotice"]
    assert "CollegeFootballData.com" not in payload["attribution"]["statement"]
    schools = [team["school"] for team in payload["teams"]]
    assert schools == [
        "Empty Roster College",
        "Fixture Falcons University",
        "Sample State Polytechnic",
    ]
    serialized = first.text
    assert "logos" not in serialized
    assert "twitter" not in serialized
    assert "Alabama" not in serialized

    second = fixture_client.get("/teams", params={"season": 2025})
    assert second.json()["cache"]["hit"] is True

    status = fixture_client.get("/refresh-status")
    team_refreshes = [row for row in status.json()["refreshes"] if row["resource"] == "teams"]
    assert len(team_refreshes) == 1
    assert team_refreshes[0]["recordsWritten"] == 3
    assert team_refreshes[0]["origin"] == "fixture"

    team = next(item for item in payload["teams"] if item["school"] == "Fixture Falcons University")
    stats = fixture_client.get(f"/teams/{team['id']}/stats", params={"season": 2025})
    assert stats.status_code == 200
    stat_body = stats.json()
    assert stat_body["cache"]["hit"] is False
    by_name = {item["name"]: item for item in stat_body["stats"]}
    assert by_name["totalYards"]["valueText"] == "1,234"
    assert by_name["totalYards"]["valueNumeric"] == 1234
    assert by_name["possessionTime"]["valueNumeric"] is None
    assert by_name["possessionTime"]["valueText"] == "99:99"
    assert "statValue" not in stats.text
    assert "statName" not in stats.text

    again = fixture_client.get(f"/teams/{team['id']}/stats", params={"season": 2025})
    assert again.json()["cache"]["hit"] is True

    empty = next(item for item in payload["teams"] if item["school"] == "Empty Roster College")
    empty_stats = fixture_client.get(f"/teams/{empty['id']}/stats", params={"season": 2025})
    assert empty_stats.status_code == 200
    assert empty_stats.json()["stats"] == []


def test_fixture_games_are_labeled_cached_and_not_a_betting_slip(fixture_client):
    listed = fixture_client.get("/teams", params={"season": 2025})
    teams = {item["school"]: item["id"] for item in listed.json()["teams"]}

    first = fixture_client.get("/games", params={"season": 2025})
    assert first.status_code == 200
    body = first.json()
    assert body["cache"]["hit"] is False
    assert body["attribution"]["dataMode"] == "fixture"
    assert "NOT REAL COLLEGE FOOTBALL STATISTICS" in body["attribution"]["fixtureNotice"]
    assert "spread" not in first.text
    assert "betting" not in first.text
    assert "moneyline" not in first.text.lower()
    assert "logos" not in first.text
    assert len(body["games"]) == 2
    final = next(game for game in body["games"] if game["status"] == "final")
    assert final["homeSchool"] == "Fixture Falcons University"
    assert final["homePoints"] == 24
    assert final["awayPoints"] == 10
    assert final["homeTeamId"] == teams["Fixture Falcons University"]
    scheduled = next(game for game in body["games"] if game["status"] == "scheduled")
    assert scheduled["homePoints"] is None
    assert scheduled["awayPoints"] is None
    assert scheduled["venue"] == "Placeholder Stadium"

    second = fixture_client.get("/games", params={"season": 2025})
    assert second.json()["cache"]["hit"] is True
    refreshes = [
        row for row in fixture_client.get("/refresh-status").json()["refreshes"] if row["resource"] == "games"
    ]
    assert len(refreshes) == 1

    falcons = fixture_client.get("/games", params={"season": 2025, "teamId": teams["Fixture Falcons University"]})
    assert len(falcons.json()["games"]) == 2
    empty = fixture_client.get("/games", params={"season": 2025, "teamId": teams["Empty Roster College"]})
    assert len(empty.json()["games"]) == 1

    early = fixture_client.get("/games", params={"season": 1999})
    assert early.status_code == 422
    assert early.json()["error"]["code"] == "SEASON_OUT_OF_RANGE"


def test_live_games_read_does_not_call_the_provider(unconfigured_live_client):
    response = unconfigured_live_client.get("/games", params={"season": 2025})
    assert response.status_code == 200
    body = response.json()
    assert body["games"] == []
    assert body["cache"]["hit"] is False
    assert body["attribution"]["dataMode"] == "live"
    assert body["attribution"]["providerName"] == "CollegeFootballData.com"
    assert unconfigured_live_client.get("/refresh-status").json()["refreshes"] == []


def test_validation_and_missing_team(fixture_client):
    missing = fixture_client.get("/teams")
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "VALIDATION_ERROR"

    early = fixture_client.get("/teams", params={"season": 1999})
    assert early.status_code == 422
    assert early.json()["error"]["code"] == "SEASON_OUT_OF_RANGE"

    absent = fixture_client.get("/teams/999999/stats", params={"season": 2025})
    assert absent.status_code == 404
    assert absent.json()["error"]["code"] == "TEAM_NOT_FOUND"


def test_live_mode_without_a_key_is_a_structured_error(unconfigured_live_client):
    response = unconfigured_live_client.get("/teams", params={"season": 2025})
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "CFBD_NOT_CONFIGURED"
    assert "collegefootballdata.com/key" in body["error"]["details"]["howTo"]
    refreshes = unconfigured_live_client.get("/refresh-status").json()["refreshes"]
    assert refreshes[0]["status"] == "error"
    assert refreshes[0]["errorCode"] == "CFBD_NOT_CONFIGURED"


def test_mocked_upstream_is_cached_and_not_passed_through(tmp_path, monkeypatch):
    """The upstream body in this test is the synthetic fixture, returned by a mock.

    It checks the live code path. It does not contact CollegeFootballData.com
    and it is not evidence about any real team.
    """

    database = tmp_path / "live-mock.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("CFIP_DATA_MODE", "live")
    monkeypatch.setenv("CFBD_API_KEY", "test-key")
    monkeypatch.setenv("CFBD_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("CFBD_CACHE_TTL_SECONDS", "86400")

    from app.config import get_settings
    from app.db import dispose_engine

    get_settings.cache_clear()
    dispose_engine()

    calls = {"teams": 0, "stats": 0}
    teams = load_fixture_list("teams.json", "teams")
    stats = [
        {**row, "season": 2024}
        for row in load_fixture_list("team_season_stats.json", "stats")
        if row["team"] == "Fixture Falcons University"
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        if request.url.path == "/teams":
            calls["teams"] += 1
            return httpx.Response(200, json=teams, headers={"x-ratelimit-remaining": "999"})
        if request.url.path == "/stats/season":
            calls["stats"] += 1
            assert request.url.params["team"] == "Fixture Falcons University"
            return httpx.Response(200, json=stats, headers={"x-ratelimit-remaining": "998"})
        return httpx.Response(404, json={"missing": True})

    from app.main import create_app

    app = create_app()

    def override_client() -> CfbdClient:
        return CfbdClient(
            get_settings(),
            transport=httpx.MockTransport(handler),
            sleeper=lambda _delay: None,
        )

    from app.api import get_client

    app.dependency_overrides[get_client] = override_client
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        listed = client.get("/teams", params={"season": 2024})
        assert listed.status_code == 200
        assert listed.json()["cache"]["hit"] is False
        assert listed.json()["attribution"]["dataMode"] == "live"
        assert listed.json()["attribution"]["providerName"] == "CollegeFootballData.com"
        assert "logos" not in listed.text
        again = client.get("/teams", params={"season": 2024})
        assert again.json()["cache"]["hit"] is True
        team_id = next(
            item["id"] for item in listed.json()["teams"] if item["school"] == "Fixture Falcons University"
        )
        stats_response = client.get(f"/teams/{team_id}/stats", params={"season": 2024})
        assert stats_response.status_code == 200
        assert stats_response.json()["stats"]
        repeat = client.get(f"/teams/{team_id}/stats", params={"season": 2024})
        assert repeat.json()["cache"]["hit"] is True

    assert calls == {"teams": 1, "stats": 1}
    dispose_engine()
    get_settings.cache_clear()


def test_alembic_upgrade_matches_the_models(tmp_path, monkeypatch):
    database = tmp_path / "migrated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    from sqlalchemy import inspect

    from app.config import get_settings
    from app.db import Base, dispose_engine, get_engine
    from app.migrate import run_migrations

    get_settings.cache_clear()
    dispose_engine()
    run_migrations()
    inspector = inspect(get_engine())
    db_tables = set(inspector.get_table_names())
    assert set(Base.metadata.tables) <= db_tables
    assert "alembic_version" in db_tables
    for name, table in Base.metadata.tables.items():
        columns = {column["name"] for column in inspector.get_columns(name)}
        assert columns == {column.name for column in table.columns}
    dispose_engine()
    get_settings.cache_clear()
