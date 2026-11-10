"""Load synthetic fixtures. These files are not recordings of the data provider."""

import json
from pathlib import Path

from app.config import BACKEND_ROOT
from app.errors import AppError
from app.normalize import FIXTURE_LABEL

FIXTURE_DIR = BACKEND_ROOT / "fixtures"


def load_fixture_list(filename: str, list_key: str) -> list:
    path = FIXTURE_DIR / filename
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AppError("FIXTURE_MISSING", f"Fixture file {filename} is missing.", 500) from exc
    except json.JSONDecodeError as exc:
        raise AppError("FIXTURE_INVALID", f"Fixture file {filename} is not valid JSON.", 500) from exc
    if not isinstance(raw, dict):
        raise AppError("FIXTURE_UNLABELED", f"Fixture file {filename} has no label object.", 500)
    notice = raw.get("_fixture")
    if not isinstance(notice, str) or FIXTURE_LABEL not in notice:
        raise AppError(
            "FIXTURE_UNLABELED",
            f"Fixture file {filename} is missing the required synthetic-data label.",
            500,
        )
    rows = raw.get(list_key)
    if not isinstance(rows, list):
        raise AppError("FIXTURE_INVALID", f"Fixture file {filename} has no {list_key} list.", 500)
    return rows
