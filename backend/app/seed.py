"""Idempotent reference rows required before ingestion."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataSource

SOURCES = (
    {
        "code": "cfbd",
        "name": "CollegeFootballData.com",
        "base_url": "https://api.collegefootballdata.com",
        "terms_url": "https://collegefootballdata.com/terms",
        "notes": (
            "Live source. Free tier documented at 1,000 calls per month as of "
            "2026-11-10. The API key stays on the server. CFIP stores normalized "
            "fields only and does not expose raw upstream responses."
        ),
    },
    {
        "code": "cfip_fixture",
        "name": "CFIP synthetic fixture",
        "base_url": "fixture://cfip/fixtures",
        "terms_url": "https://collegefootballdata.com/terms",
        "notes": (
            "Synthetic records for tests and for UI review when no CFBD key is "
            "configured. Not college football statistics. Not from CollegeFootballData.com."
        ),
    },
)


def seed_sources(db: Session) -> None:
    for spec in SOURCES:
        existing = db.scalar(select(DataSource).where(DataSource.code == spec["code"]))
        if existing is None:
            db.add(DataSource(**spec))
        else:
            existing.name = spec["name"]
            existing.base_url = spec["base_url"]
            existing.terms_url = spec["terms_url"]
            existing.notes = spec["notes"]
    db.commit()
