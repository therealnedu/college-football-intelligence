import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.errors import AppError
from app.fixtures_loader import load_fixture_list
from app.normalize import normalize_games, normalize_stats, normalize_teams, parse_stat_value

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


def test_normalize_games_drops_betting_fields_and_keeps_a_missing_score_null():
    games, skipped = normalize_games(
        [
            {
                "id": 7,
                "season": 2024,
                "week": 1,
                "season_type": "regular",
                "start_date": "2024-09-01T20:00:00Z",
                "completed": True,
                "neutral_site": False,
                "venue": "Recorded Field",
                "home_id": 1,
                "home_team": "Home College",
                "home_points": 17,
                "away_id": 2,
                "away_team": "Away College",
                "away_points": None,
                "betting": {"spread": -3, "overUnder": 50, "homeMoneyline": -120},
                "homeLineScores": [7, 0],
                "logos": ["https://example.invalid/logo.png"],
            },
            {
                "id": 8,
                "season": 2024,
                "week": 2,
                "seasonType": "regular",
                "completed": True,
                "homeTeam": {"id": 2, "name": "Away College", "points": True},
                "awayTeam": {"school": "Home College", "id": 1, "points": "10"},
                "venue": {"name": "Nested Yard", "city": "Nowhere"},
            },
            {"id": 9, "season": 2024, "homeTeam": "Only Home"},
            "not-an-object",
        ]
    )
    assert skipped == 2
    assert games[0].away_points is None
    assert games[0].home_points == 17
    assert games[0].status == "final"
    dumped = games[0].model_dump()
    assert "betting" not in dumped
    assert "spread" not in dumped
    assert "logos" not in dumped
    assert games[1].home_school == "Away College"
    assert games[1].home_points is None
    assert games[1].away_points == 10
    assert games[1].venue == "Nested Yard"


def test_normalize_games_rejects_a_non_list():
    with pytest.raises(AppError) as caught:
        normalize_games({"games": []})
    assert caught.value.code == "UPSTREAM_INVALID"


def test_checked_in_fixtures_are_labeled_and_synthetic():
    for name in ("teams.json", "team_season_stats.json", "games.json"):
        raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        assert "NOT REAL COLLEGE FOOTBALL STATISTICS" in raw["_fixture"]
        assert "Alabama" not in json.dumps(raw)
    teams = load_fixture_list("teams.json", "teams")
    schools = {row["school"] for row in teams}
    assert "Fixture Falcons University" in schools
    assert "Alabama" not in schools
    stats = load_fixture_list("team_season_stats.json", "stats")
    assert all(row["statValue"] in {100, 40, "1,234", 3, "99:99", 1, 20, 10, 2} for row in stats)
