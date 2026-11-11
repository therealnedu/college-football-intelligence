"""Command line: load one season and optionally write the static snapshot.

Examples, from the backend directory:

    python -m app.ingest --season auto --snapshot ../frontend/public/data/snapshot.json
    python -m app.ingest --season 2025 --force --allow-fixture-fallback --snapshot ../frontend/public/data/snapshot.json

`--season auto` is the previous calendar year. That avoids treating the
in-progress season as a complete one. `--force` ignores the 24-hour cache.
The GitHub Actions database is empty on every run; the workflow still passes
`--force` so a rerun inside one job cannot skip the provider.

Exit codes: 0 stored, 1 a resource failed, 2 a live run was requested and no
key is set. `--allow-fixture-fallback` turns that last case into a labeled
fixture load and exit 0.
"""

import argparse
import sys

from app.cfbd import CfbdClient
from app.config import Settings, get_settings
from app.db import dispose_engine, session_factory
from app.errors import AppError
from app.migrate import run_migrations
from app.pipeline import IngestReport, run_ingest
from app.seed import seed_sources
from app.snapshot_export import build_snapshot, write_snapshot


class IngestNotConfigured(Exception):
    pass


def select_settings(settings: Settings, allow_fixture_fallback: bool) -> tuple[Settings, str]:
    """Pick fixture or live for this process without reading a new environment."""

    if settings.fixture_mode:
        return settings, ""
    if settings.cfbd_api_key.strip():
        return settings, ""
    if allow_fixture_fallback:
        switched = settings.model_copy(update={"cfip_data_mode": "fixture"})
        return switched, (
            "CFBD_API_KEY is not set. This run is using labeled fixture data and will not "
            "call CollegeFootballData.com."
        )
    raise IngestNotConfigured(
        "CFBD_API_KEY is not set, so live ingest cannot run. Request a free key at "
        "https://collegefootballdata.com/key and export it as CFBD_API_KEY, or pass "
        "--allow-fixture-fallback to build the labeled synthetic snapshot."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load one CFIP season and optionally write a static snapshot.")
    parser.add_argument(
        "--season",
        default="auto",
        help="Season year, or 'auto' for the previous calendar year.",
    )
    parser.add_argument("--snapshot", default="", help="Write the public snapshot JSON to this path.")
    parser.add_argument("--force", action="store_true", help="Refresh even if a successful load is still inside the cache TTL.")
    parser.add_argument(
        "--allow-fixture-fallback",
        action="store_true",
        help="If no API key is set, load labeled fixtures instead of exiting 2.",
    )
    args = parser.parse_args(argv)

    try:
        settings, notice = select_settings(get_settings(), args.allow_fixture_fallback)
    except IngestNotConfigured as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if notice:
        print(notice)

    season, error = _resolve_season(args.season, settings)
    if error:
        print(error, file=sys.stderr)
        return 2

    if settings.cfip_auto_migrate:
        run_migrations()
    db = session_factory()()
    try:
        seed_sources(db)
        try:
            report = run_ingest(
                db,
                settings,
                CfbdClient(settings),
                season,
                force=args.force,
            )
        except AppError as exc:
            print(f"{exc.code}: {exc.message}", file=sys.stderr)
            return 1
        _print_report(report)
        if not report.ok:
            return 1
        if args.snapshot:
            payload = build_snapshot(db, settings, season, report)
            write_snapshot(_snapshot_path(args.snapshot), payload)
            print(f"snapshot={args.snapshot}")
        return 0
    finally:
        db.close()
        dispose_engine()


def _resolve_season(raw: str, settings: Settings) -> tuple[int | None, str | None]:
    if raw.strip().lower() == "auto":
        return settings.default_season, None
    try:
        season = int(raw)
    except ValueError:
        return None, f"Season {raw!r} is not a year."
    if season < settings.cfip_min_season or season > settings.max_season:
        return None, (
            f"Season {season} is outside {settings.cfip_min_season} through {settings.max_season}."
        )
    return season, None


def _snapshot_path(raw: str):
    from pathlib import Path

    return Path(raw)


def _print_report(report: IngestReport) -> None:
    print(
        f"season={report.season} mode={report.data_mode} "
        f"calls={report.provider_calls} stopped={str(report.stopped_early).lower()}"
    )
    for item in report.resources:
        print(
            f"{item.resource} status={item.status} records={item.records_written} "
            f"http={item.http_status if item.http_status is not None else '-'}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
