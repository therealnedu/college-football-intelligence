import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.errors import AppError
from app.fixtures_loader import load_fixture_list
from app.normalize import normalize_stats, normalize_teams, parse_stat_value

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_stat_value_keeps_clocks_and_commas():
    number, text = parse_stat_value("1,234")
    assert number == Decimal("1234")
    assert text == "1,234"

    number, text = parse_stat_value("99:99")
    assert number is None
    assert text == "99:99"

    number, text = parse_stat_value(True)
    assert number is None
    assert text == "true"

    number, text = parse_stat_value(float("nan"))
    assert number is None


def test_normalize_teams_drops_blank_rows_and_ignores_logos():
    teams, skipped = normalize_teams(
        [
            {"id": 1, "school": "  Kept University  ", "logos": ["https://example.invalid/logo.png"], "twitter": "@x"},
            {"id": 2, "school": "   "},
            {"school": "Missing Id"},
            "not-an-object",
        ]
    )
    assert skipped == 3
    assert len(teams) == 1
    assert teams[0].school == "Kept University"
    assert not hasattr(teams[0], "logos")
    dumped = teams[0].model_dump()
    assert "logos" not in dumped
    assert "twitter" not in dumped


def test_normalize_teams_rejects_a_non_list():
    with pytest.raises(AppError) as caught:
        normalize_teams({"teams": []})
    assert caught.value.code == "UPSTREAM_INVALID"


def test_normalize_stats_preserves_text_token():
    stats, skipped = normalize_stats(
        [
            {
                "season": 2024,
                "team": "Fixture Falcons University",
                "conference": "Fixture Conference",
                "statName": "possessionTime",
                "statValue": "99:99",
                "extraUpstreamField": "drop me",
            },
            {"season": 2024, "team": "", "statName": "rushingYards", "statValue": 1},
        ]
    )
    assert skipped == 1
    assert stats[0].value_numeric is None
    assert stats[0].value_text == "99:99"
    assert "extraUpstreamField" not in stats[0].model_dump()


def test_checked_in_fixtures_are_labeled_and_synthetic():
    for name in ("teams.json", "team_season_stats.json"):
        raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        assert "NOT REAL COLLEGE FOOTBALL STATISTICS" in raw["_fixture"]
    teams = load_fixture_list("teams.json", "teams")
    schools = {row["school"] for row in teams}
    assert "Fixture Falcons University" in schools
    assert "Alabama" not in schools
    stats = load_fixture_list("team_season_stats.json", "stats")
    assert all(row["statValue"] in {100, 40, "1,234", 3, "99:99", 1, 20, 10, 2} for row in stats)
