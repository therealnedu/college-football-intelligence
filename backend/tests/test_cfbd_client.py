import httpx
import pytest

from app.cfbd import CfbdClient
from app.config import Settings
from app.errors import AppError


def _settings(**overrides) -> Settings:
    values = {
        "cfbd_api_key": "test-key",
        "cfbd_base_url": "https://provider.test",
        "cfbd_timeout_seconds": 1,
        "cfbd_max_retries": 3,
        "cfbd_backoff_seconds": 0.2,
    }
    values.update(overrides)
    return Settings(**values)


def test_missing_key_does_not_call_the_network():
    called = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json=[])

    client = CfbdClient(_settings(cfbd_api_key="  "), transport=httpx.MockTransport(handler))
    with pytest.raises(AppError) as caught:
        client.fetch_teams(2024)
    assert caught.value.code == "CFBD_NOT_CONFIGURED"
    assert caught.value.status_code == 503
    assert called["n"] == 0


def test_retries_server_errors_then_returns_json():
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.url.path == "/teams"
        assert request.url.params["year"] == "2024"
        if calls["n"] < 3:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json=[{"id": 1, "school": "Fixture"}])

    client = CfbdClient(
        _settings(),
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
    )
    result = client.fetch_teams(2024)
    assert result.http_status == 200
    assert result.payload == [{"id": 1, "school": "Fixture"}]
    assert calls["n"] == 3
    assert sleeps == [0.2, 0.4]


def test_long_retry_after_fails_fast():
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"retry-after": "120", "x-ratelimit-remaining": "0"})

    client = CfbdClient(_settings(), transport=httpx.MockTransport(handler), sleeper=lambda _delay: None)
    with pytest.raises(AppError) as caught:
        client.fetch_team_season_stats(2024, "Fixture Falcons University")
    assert caught.value.code == "CFBD_RATE_LIMITED"
    assert caught.value.status_code == 429
    assert caught.value.details["retryAfterSeconds"] == 120
    assert calls["n"] == 1


def test_timeouts_are_retried_then_reported():
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.TimeoutException("timed out")

    client = CfbdClient(_settings(cfbd_max_retries=2), transport=httpx.MockTransport(handler), sleeper=lambda _d: None)
    with pytest.raises(AppError) as caught:
        client.fetch_teams(2024)
    assert caught.value.code == "CFBD_TIMEOUT"
    assert calls["n"] == 2


def test_unauthorized_is_not_retried():
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"message": "bad key"})

    client = CfbdClient(_settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(AppError) as caught:
        client.fetch_teams(2024)
    assert caught.value.code == "CFBD_UNAUTHORIZED"
    assert "test-key" not in caught.value.message
    assert calls["n"] == 1
