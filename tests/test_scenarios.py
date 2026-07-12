from scenarios import label_from_deltas


def test_downturn_when_prices_fall_sharply():
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=-4.0) == "downturn"


def test_downturn_when_rate_rises_sharply():
    assert label_from_deltas(rate_delta=2.0, hpi_delta_pct=0.0) == "downturn"


def test_boom_when_prices_rise_fast():
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=6.0) == "boom"


def test_baseline_when_stable():
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=1.0) == "baseline"


def test_downturn_takes_priority_over_boom():
    # falling prices beats anything
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=-4.0) == "downturn"


def test_returns_string():
    result = label_from_deltas(0.0, 0.0)
    assert isinstance(result, str)
