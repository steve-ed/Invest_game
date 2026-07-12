import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dummy_data import trend, trend_arrow, portfolio_value, gross_yield, GAME_STATE, START_STATE


def test_trend_up():
    assert trend(112.4, 109.1) == "up"


def test_trend_down():
    assert trend(4.5, 5.0) == "down"


def test_trend_flat():
    assert trend(5.0, 5.0) == "flat"


def test_trend_arrow_up():
    assert trend_arrow("up") == "^"


def test_trend_arrow_down():
    assert trend_arrow("down") == "v"


def test_trend_arrow_flat():
    assert trend_arrow("flat") == "-"


def test_portfolio_value():
    player = {"portfolio": [{"value": 182000, "rent": 755}, {"value": 158000, "rent": 630}]}
    assert portfolio_value(player) == 340000


def test_gross_yield():
    prop = {"value": 180000, "rent": 750}
    assert abs(gross_yield(prop) - 5.0) < 0.01


def test_game_state_keys():
    for key in ("tick", "total_ticks", "scenario", "macro", "player", "ai", "market", "news", "leaderboard", "end"):
        assert key in GAME_STATE, f"Missing: {key}"


def test_start_state_keys():
    for key in ("tick", "total_ticks", "scenario", "macro", "actors", "market"):
        assert key in START_STATE, f"Missing: {key}"


def test_ai_entries_have_required_fields():
    for ai in GAME_STATE["ai"]:
        assert "last_property" in ai, f"{ai['name']} missing last_property"
        assert "rationale" in ai, f"{ai['name']} missing rationale"
