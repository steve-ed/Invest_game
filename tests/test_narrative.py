from state import SimulationState
from narrative.branching import BranchingEngine, HIGH_RATE_THRESHOLD
from narrative.scenario_events import ScenarioEventEngine


def test_stress_branch_when_rate_high():
    state = SimulationState()
    state.macro.interest_rate = HIGH_RATE_THRESHOLD + 0.01
    engine = BranchingEngine()
    events = engine.step(state, tick=1)
    assert events[0]["branch"] == "stress"


def test_stable_branch_when_rate_normal():
    state = SimulationState()
    state.macro.interest_rate = 0.04
    engine = BranchingEngine()
    events = engine.step(state, tick=1)
    assert events[0]["branch"] == "stable"


def test_branching_returns_event_dict():
    state = SimulationState()
    engine = BranchingEngine()
    events = engine.step(state, tick=3)
    assert len(events) == 1
    assert events[0]["type"] == "narrative_branch"
    assert events[0]["tick"] == 3
    assert "detail" in events[0]


def test_scenario_event_returns_event_dict():
    state = SimulationState()
    state.current_scenario = "baseline"
    engine = ScenarioEventEngine()
    events = engine.step(state, tick=1)
    assert len(events) == 1
    assert events[0]["type"] == "scenario_event"
    assert isinstance(events[0]["detail"], str)
    assert len(events[0]["detail"]) > 0


def test_scenario_event_varies_by_scenario():
    engine = ScenarioEventEngine()
    baseline_state = SimulationState()
    baseline_state.current_scenario = "baseline"
    downturn_state = SimulationState()
    downturn_state.current_scenario = "downturn"
    baseline_events = engine.step(baseline_state, tick=1)
    downturn_events = engine.step(downturn_state, tick=1)
    assert baseline_events[0]["detail"] != downturn_events[0]["detail"]
