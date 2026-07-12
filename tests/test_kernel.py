import json
import os
import tempfile
from kernel import SimulationKernel


def test_run_returns_trace_with_correct_tick_count():
    kernel = SimulationKernel(turns=5, turn_delay=0)
    results = kernel.run()
    assert len(results["trace"]) == 5


def test_state_tick_advances_each_turn():
    kernel = SimulationKernel(turns=3, turn_delay=0)
    kernel.run()
    assert kernel.state.tick == 3


def test_macro_values_come_from_uk_macro_slice():
    kernel = SimulationKernel(turns=3, turn_delay=0)
    kernel.run()
    assert kernel.state.macro.price_index > 0


def test_state_has_era_fields_after_init():
    kernel = SimulationKernel(turns=5, turn_delay=0)
    assert kernel.state.start_year > 0
    assert kernel.state.start_half in (1, 2)
    assert kernel.state.era_label != ""


def test_trace_contains_property_valuation_events():
    kernel = SimulationKernel(turns=2, turn_delay=0)
    results = kernel.run()
    all_events = [e for tick in results["trace"] for e in tick["events"]]
    valuation_events = [e for e in all_events if e["type"] == "property_valuation"]
    assert len(valuation_events) > 0


def test_leaderboard_present_in_results():
    kernel = SimulationKernel(turns=2, turn_delay=0)
    results = kernel.run()
    assert "leaderboard" in results
    assert len(results["leaderboard"]) > 0


def test_macro_interest_rate_is_decimal():
    # interest_rate must be stored as decimal (e.g. 0.085 not 8.5)
    kernel = SimulationKernel(turns=2, turn_delay=0)
    kernel.run()
    assert kernel.state.macro.interest_rate < 1.0


def test_turn_state_json_written(tmp_path, monkeypatch):
    json_path = tmp_path / "turn_state.json"
    monkeypatch.setattr("kernel.TURN_STATE_PATH", str(json_path))
    kernel = SimulationKernel(turns=2, turn_delay=0)
    kernel.run()
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert "tick" in data
    assert "macro_history" in data
    assert "wealth_history" in data
