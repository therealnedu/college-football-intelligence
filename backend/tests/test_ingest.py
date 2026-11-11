"""Ingest tests replay synthetic recorded responses. They do not call the provider."""

import json
from pathlib import Path

import httpx
import pytest

from app.cfbd import CfbdClient
from app.config import Settings, get_settings
from app.db import dispose_engine, session_factory
from app.errors import AppError
from app.ingest import main, select_settings
from app.migrate import run_migrations
from app.pipeline import run_ingest
from app.seed import seed_sources
from app.snapshot_export import build_snapshot, write_snapshot

RECORDED = Path(__file__).resolve().parent / "recorded"
LABEL = "NOT REAL COLLEGE FOOTBALL STATISTICS"


def _load_recorded() -> dict:
    raw = json.loads((RECORDED / "season.json").read_text(encoding="utf-8"))
    if LABEL not in raw.get("_fixture", ""):
        raise AssertionError("Recorded response is missing the synthetic-data label.")
    return raw


def _settings(database: Path, **overrides) -> Settings:
    values = {
        "cfbd_api_key": "test-key",
        "cfbd_base_url": "https://provider.test",
        "cfbd_timeout_seconds": 1,
        "cfbd_max_retries": 3,
        "cfbd_backoff_seconds": 0,
        "cfbd_cache_ttl_seconds": 86_400,
        "database_url": f"sqlite:///{database}",
        "cfip_data_mode": "live",
        "cfip_auto_migrate": True,
        "cfip_ingest_classification": "fbs",
        "cfip_ingest_pause_seconds": 0,
        "cfip_ingest_min_remaining": 25,
        "cfip_max_season": 2026,
    }
    values.update(overrides)
    return Settings(**values)


def _prepare(database: Path, monkeypatch, settings: Settings):
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("CFIP_DATA_MODE", settings.cfip_data_mode)
    monkeypatch.setenv("CFBD_API_KEY", settings.cfbd_api_key)
    monkeypatch.setenv("CFIP_AUTO_MIGRATE", "true")
    get_settings.cache_clear()
    dispose_engine()
    run_migrations()
    db = session_factory()()
    seed_sources(db)
    return db


def test_recorded_file_is_labeled():
    recorded = _load_recorded()
    assert "Alabama" not in json.dumps(recorded)
    assert any(row["classification"] == "fcs" for row in recorded["teams"])


def test_live_ingest_is_idempotent_and_drops_provider_only_fields(tmp_path, monkeypatch):
    database = tmp_path / "ingest.db"
    settings = _settings(database)
    recorded = _load_recorded()
    calls: list[str] = []
    sleeps: list[float] = []
    state = {"games": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        if request.url.path == "/teams":
            calls.append("teams")
            assert request.url.params["year"] == "2024"
            return httpx.Response(200, json=recorded["teams"], headers={"x-ratelimit-remaining": "900"})
        if request.url.path == "/games":
            calls.append("games")
            state["games"] += 1
            assert request.url.params["seasonType"] == "both"
            assert request.url.params["classification"] == "fbs"
            games = json.loads(json.dumps(recorded["games"]))
            if state["games"] > 1:
                games[0]["home_points"] = 30
            return httpx.Response(200, json=games, headers={"x-ratelimit-remaining": "899"})
        if request.url.path == "/stats/season":
            calls.append("stats")
            assert request.url.params["year"] == "2024"
            assert request.url.params["classification"] == "fbs"
            assert "team" not in request.url.params
            return httpx.Response(200, json=recorded["stats"], headers={"x-ratelimit-remaining": "898"})
        return httpx.Response(404, json={"missing": True})

    db = _prepare(database, monkeypatch, settings)
    try:
        client = CfbdClient(settings, transport=httpx.MockTransport(handler), sleeper=lambda _delay: None)
        first = run_ingest(db, settings, client, 2024, force=True, pause_seconds=0.25, sleeper=sleeps.append)
        assert first.ok
        assert first.provider_calls == 3
        assert [item.resource for item in first.resources] == ["teams", "games", "season_stats"]
        assert sleeps == [0.25, 0.25]
        payload = build_snapshot(db, settings, 2024, first)
        text = json.dumps(payload)
        schools = [team["school"] for team in payload["teams"]]
        assert schools == ["Kept Falcon College", "Kept River College"]
        assert "Dropped Cellar College" not in schools
        assert "Dropped Cellar College" in text
        assert payload["dataMode"] == "live"
        assert payload["ingest"]["providerCalls"] == 3
        assert "NOT REAL COLLEGE FOOTBALL STATISTICS" not in payload["attribution"]["statement"]
        for banned in ("spread", "betting", "moneyline", "logos", "twitter", "statValue", "statName"):
            assert banned not in text
        falcon = next(team for team in payload["teams"] if team["school"] == "Kept Falcon College")
        stats = {item["name"]: item for item in payload["statsByTeamId"][str(falcon["id"])]}
        assert stats["totalYards"]["valueText"] == "1,234"
        assert stats["totalYards"]["valueNumeric"] == 1234
        assert stats["possessionTime"]["valueNumeric"] is None
        assert "rushingYards" not in stats
        final = next(game for game in payload["games"] if game["externalId"] == 810001)
        assert final["homePoints"] == 17
        assert final["awayPoints"] == 14
        opponent = next(game for game in payload["games"] if game["externalId"] == 810002)
        assert opponent["homePoints"] == 7
        assert opponent["awayPoints"] == 21
        assert opponent["homeTeamId"] is None
        assert opponent["venue"] == "Cellar Yard"

        skipped = run_ingest(db, settings, client, 2024, force=False, pause_seconds=1, sleeper=sleeps.append)
        assert skipped.ok
        assert skipped.provider_calls == 0
        assert [item.status for item in skipped.resources] == ["skipped", "skipped", "skipped"]

        updated = run_ingest(db, settings, client, 2024, force=True, pause_seconds=0, sleeper=lambda _delay: None)
        assert updated.provider_calls == 3
        again = build_snapshot(db, settings, 2024, updated)
        assert len(again["teams"]) == 2
        assert len(again["games"]) == 2
        revised = next(game for game in again["games"] if game["externalId"] == 810001)
        assert revised["homePoints"] == 30
    finally:
        db.close()
        dispose_engine()
        get_settings.cache_clear()


def test_low_remaining_stops_before_the_next_call(tmp_path, monkeypatch):
    database = tmp_path / "guard.db"
    settings = _settings(database, cfip_ingest_min_remaining=25)
    recorded = _load_recorded()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=recorded["teams"], headers={"x-ratelimit-remaining": "10"})

    db = _prepare(database, monkeypatch, settings)
    try:
        client = CfbdClient(settings, transport=httpx.MockTransport(handler), sleeper=lambda _delay: None)
        report = run_ingest(db, settings, client, 2024, force=True, pause_seconds=5, sleeper=lambda _delay: None)
        assert report.stopped_early
        assert report.ok
        assert report.provider_calls == 1
        assert calls == ["/teams"]
        assert [item.status for item in report.resources] == ["success", "stopped", "stopped"]
        payload = build_snapshot(db, settings, 2024, report)
        assert payload["games"] == []
        assert payload["ingest"]["stoppedEarly"] is True
        assert "Partial live load" in payload["ingest"]["note"]
    finally:
        db.close()
        dispose_engine()
        get_settings.cache_clear()


def test_a_non_list_games_payload_fails_the_run_without_a_stats_call(tmp_path, monkeypatch):
    database = tmp_path / "bad.db"
    settings = _settings(database)
    recorded = _load_recorded()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/games":
            return httpx.Response(200, json={"games": []})
        if request.url.path == "/teams":
            return httpx.Response(200, json=recorded["teams"], headers={"x-ratelimit-remaining": "100"})
        return httpx.Response(500, json={"no": True})

    db = _prepare(database, monkeypatch, settings)
    try:
        client = CfbdClient(settings, transport=httpx.MockTransport(handler), sleeper=lambda _delay: None)
        report = run_ingest(db, settings, client, 2024, force=True, pause_seconds=0)
        assert not report.ok
        assert calls == ["/teams", "/games"]
        games = next(item for item in report.resources if item.resource == "games")
        assert games.status == "error"
        assert games.error_code == "UPSTREAM_INVALID"
        assert all(item.resource != "season_stats" for item in report.resources)
    finally:
        db.close()
        dispose_engine()
        get_settings.cache_clear()


def test_select_settings_and_cli_fallback(tmp_path, monkeypatch, capsys):
    live = Settings(cfbd_api_key="present", cfip_data_mode="live")
    chosen, note = select_settings(live, allow_fixture_fallback=False)
    assert chosen.fixture_mode is False
    assert note == ""

    missing = Settings(cfbd_api_key="", cfip_data_mode="live")
    with pytest.raises(Exception) as caught:
        select_settings(missing, allow_fixture_fallback=False)
    assert "collegefootballdata.com/key" in str(caught.value)

    fallback, note = select_settings(missing, allow_fixture_fallback=True)
    assert fallback.fixture_mode is True
    assert "fixture" in note.lower()
    assert missing.fixture_mode is False

    database = tmp_path / "cli.db"
    snapshot = tmp_path / "snapshot.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("CFIP_DATA_MODE", "live")
    monkeypatch.setenv("CFBD_API_KEY", "   ")
    monkeypatch.setenv("CFIP_INGEST_PAUSE_SECONDS", "0")
    monkeypatch.setenv("CFIP_MAX_SEASON", "2026")
    get_settings.cache_clear()
    dispose_engine()

    code = main(["--season", "2025", "--snapshot", str(snapshot)])
    assert code == 2
    assert "collegefootballdata.com/key" in capsys.readouterr().err
    assert not snapshot.exists()

    code = main(
        [
            "--season",
            "2025",
            "--force",
            "--allow-fixture-fallback",
            "--snapshot",
            str(snapshot),
        ]
    )
    assert code == 0
    first = json.loads(snapshot.read_text(encoding="utf-8"))
    assert first["dataMode"] == "fixture"
    assert LABEL in first["attribution"]["fixtureNotice"]
    assert first["ingest"]["providerCalls"] == 0
    assert len(first["teams"]) == 3
    assert len(first["games"]) == 2
    text = snapshot.read_text(encoding="utf-8")
    assert "spread" not in text
    assert "betting" not in text
    assert "logos" not in text

    captured = capsys.readouterr()
    code = main(["--season", "2025", "--allow-fixture-fallback", "--snapshot", str(snapshot)])
    assert code == 0
    second_out = captured.out + capsys.readouterr().out
    assert "teams status=skipped" in second_out
    second = json.loads(snapshot.read_text(encoding="utf-8"))
    assert [team["school"] for team in second["teams"]] == [team["school"] for team in first["teams"]]
    dispose_engine()
    get_settings.cache_clear()


def test_write_snapshot_refuses_a_banned_key(tmp_path):
    with pytest.raises(AppError) as caught:
        write_snapshot(tmp_path / "bad.json", {"dataMode": "live", "spread": 1, "attribution": {}})
    assert caught.value.code == "SNAPSHOT_UNSAFE"
    assert not (tmp_path / "bad.json").exists()
