"""CollegeFootballData.com HTTP client.

Timeouts, retries, and rate-limit handling live here. The client returns the
parsed JSON to the catalog, which immediately normalizes it. Raw bodies are
not logged and are not stored.
"""

import time
from dataclasses import dataclass

import httpx

from app.config import Settings
from app.errors import AppError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_BLOCKING_RETRY_SECONDS = 30


@dataclass(frozen=True)
class CfbdResult:
    payload: object
    http_status: int
    rate_limit_remaining: str | None


class CfbdClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleeper=time.sleep,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._sleeper = sleeper

    def fetch_teams(self, season: int) -> CfbdResult:
        return self.get_json("/teams", {"year": season})

    def fetch_team_season_stats(self, season: int, school: str) -> CfbdResult:
        # /stats/season is the documented team-season operation. An unauthenticated
        # probe on 2026-11-10 returned 401 for this path and 404 for /stats/team/season.
        return self.get_json("/stats/season", {"year": season, "team": school})

    def fetch_games(self, season: int, classification: str | None = None) -> CfbdResult:
        """One call for the season schedule and results.

        `seasonType=both` is regular season plus postseason. All-star games
        are not requested. Betting lines live on a different route and are
        not requested here.
        """

        params: dict[str, object] = {"year": season, "seasonType": "both"}
        if classification:
            params["classification"] = classification
        return self.get_json("/games", params)

    def fetch_season_stats(self, season: int, classification: str | None = None) -> CfbdResult:
        """One call for every team's season stats in a classification.

        The documented operation requires `year` or `team`. Passing `year`
        without `team` is the bulk read. The provider default classification
        is FBS; this client sends the classification explicitly when asked.
        """

        params: dict[str, object] = {"year": season}
        if classification:
            params["classification"] = classification
        return self.get_json("/stats/season", params)

    def get_json(self, path: str, params: dict) -> CfbdResult:
        key = self.settings.cfbd_api_key.strip()
        if not key:
            raise AppError(
                "CFBD_NOT_CONFIGURED",
                "CFBD_API_KEY is not set, so live retrieval from CollegeFootballData.com is unavailable.",
                503,
                {
                    "howTo": (
                        "Request a free key at https://collegefootballdata.com/key "
                        "and export it as CFBD_API_KEY. Do not commit the key."
                    )
                },
            )

        attempts = max(1, self.settings.cfbd_max_retries)
        timeout = httpx.Timeout(self.settings.cfbd_timeout_seconds)
        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "cfip/0.2 (server-side portfolio client)",
        }
        last_error: AppError | None = None
        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(
                    base_url=self.settings.cfbd_base_url.rstrip("/"),
                    timeout=timeout,
                    transport=self._transport,
                    headers=headers,
                ) as client:
                    response = client.get(path, params=params)
            except httpx.TimeoutException as exc:
                last_error = AppError(
                    "CFBD_TIMEOUT",
                    "CollegeFootballData.com did not respond before the timeout.",
                    504,
                    {"attempts": attempt},
                )
                if attempt == attempts:
                    raise last_error from exc
                self._backoff(attempt, None)
                continue
            except httpx.HTTPError as exc:
                last_error = AppError(
                    "CFBD_UNAVAILABLE",
                    "CollegeFootballData.com could not be reached.",
                    502,
                    {"attempts": attempt, "reason": type(exc).__name__},
                )
                if attempt == attempts:
                    raise last_error from exc
                self._backoff(attempt, None)
                continue

            if response.status_code in RETRYABLE_STATUS:
                retry_after = _retry_after_seconds(response)
                if retry_after is not None and retry_after > MAX_BLOCKING_RETRY_SECONDS:
                    raise AppError(
                        "CFBD_RATE_LIMITED",
                        "CollegeFootballData.com asked us to wait longer than a web request can block.",
                        429,
                        {"retryAfterSeconds": retry_after, "attempts": attempt},
                    )
                last_error = _error_for_status(response, attempt)
                if attempt == attempts:
                    raise last_error
                self._backoff(attempt, response)
                continue

            if response.status_code >= 400:
                raise _error_for_status(response, attempt)

            try:
                payload = response.json()
            except ValueError as exc:
                raise AppError(
                    "CFBD_INVALID_RESPONSE",
                    "CollegeFootballData.com returned a body that is not JSON.",
                    502,
                    {"attempts": attempt},
                ) from exc
            return CfbdResult(
                payload=payload,
                http_status=response.status_code,
                rate_limit_remaining=_rate_limit_remaining(response),
            )

        raise last_error or AppError("CFBD_UNAVAILABLE", "CollegeFootballData.com could not be reached.", 502)

    def _backoff(self, attempt: int, response: httpx.Response | None) -> None:
        delay = self.settings.cfbd_backoff_seconds * (2 ** (attempt - 1))
        if response is not None:
            retry_after = _retry_after_seconds(response)
            if retry_after is not None:
                delay = max(delay, retry_after)
        if delay > 0:
            self._sleeper(delay)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _rate_limit_remaining(response: httpx.Response) -> str | None:
    for name in (
        "x-ratelimit-remaining",
        "x-ratelimit-remaining-requests",
        "ratelimit-remaining",
    ):
        value = response.headers.get(name)
        if value:
            return value
    return None


def _error_for_status(response: httpx.Response, attempt: int) -> AppError:
    status = response.status_code
    details = {"upstreamStatus": status, "attempts": attempt}
    remaining = _rate_limit_remaining(response)
    if remaining is not None:
        details["rateLimitRemaining"] = remaining
    if status == 401:
        return AppError(
            "CFBD_UNAUTHORIZED",
            "CollegeFootballData.com rejected the API key.",
            502,
            details,
        )
    if status == 429:
        return AppError(
            "CFBD_RATE_LIMITED",
            "CollegeFootballData.com refused the request because the quota or a rate limit was reached.",
            429,
            details,
        )
    if status >= 500:
        return AppError(
            "CFBD_UNAVAILABLE",
            "CollegeFootballData.com returned a server error.",
            502,
            details,
        )
    return AppError(
        "CFBD_BAD_REQUEST",
        "CollegeFootballData.com rejected the query.",
        502,
        details,
    )
