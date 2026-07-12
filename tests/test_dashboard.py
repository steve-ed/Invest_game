from ui.dashboard import trend_arrow, compute_yield, extract_news, portfolio_value
from state import Property


def test_trend_arrow_up():
    assert trend_arrow(101.0, 100.0) == "↑"


def test_trend_arrow_down():
    assert trend_arrow(99.0, 100.0) == "↓"


def test_trend_arrow_flat_exact():
    assert trend_arrow(100.0, 100.0) == "→"


def test_trend_arrow_flat_within_threshold():
    assert trend_arrow(100.0005, 100.0) == "→"


def test_compute_yield_six_percent():
    result = compute_yield(rent=1000.0, current_value=200000.0)
    assert abs(result - 6.0) < 0.01


def test_compute_yield_zero_value():
    assert compute_yield(rent=1000.0, current_value=0.0) == 0.0


def test_extract_news_returns_newest_first():
    events = [
        {"type": "scenario_event", "detail": "news1"},
        {"type": "narrative_branch", "detail": "news2"},
        {"type": "scenario_event", "detail": "news3"},
        {"type": "narrative_branch", "detail": "news4"},
        {"type": "scenario_event", "detail": "news5"},
        {"type": "scenario_event", "detail": "news6"},
    ]
    result = extract_news(events)
    assert len(result) == 5
    assert result[0]["detail"] == "news6"
    assert result[4]["detail"] == "news2"


def test_extract_news_excludes_non_narrative():
    events = [
        {"type": "shock", "detail": "shock"},
        {"type": "property_valuation", "detail": "val"},
    ]
    assert extract_news(events) == []


def test_portfolio_value_sums_current_values():
    prop_map = {
        "p01": Property(id="p01", region="London", base_value=500000.0, current_value=510000.0, rent=2500.0),
        "p02": Property(id="p02", region="Oxford", base_value=230000.0, current_value=235000.0, rent=1150.0),
    }
    assert portfolio_value(["p01", "p02"], prop_map) == 745000.0


def test_portfolio_value_skips_missing_ids():
    prop_map = {
        "p01": Property(id="p01", region="London", base_value=500000.0, current_value=500000.0, rent=2500.0),
    }
    assert portfolio_value(["p01", "p99"], prop_map) == 500000.0
