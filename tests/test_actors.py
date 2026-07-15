from state import SimulationState, ActorState
from actors import ActorManager


def test_cash_compounds_at_interest_rate():
    state = SimulationState()
    state.actors = {
        "a1": ActorState(id="a1", name="Investor A", cash=100000.0, risk_appetite=0.5)
    }
    state.macro.interest_rate = 0.12  # 12% annual, savings rate = 12%*0.75/2 = 4.5% semi-annual
    manager = ActorManager()
    manager.step(state, tick=1)
    assert abs(state.actors["a1"].cash - 104500.0) < 0.01


def test_step_returns_one_event_per_actor():
    state = SimulationState()
    state.actors = {
        "a1": ActorState(id="a1", name="A", cash=50000.0, risk_appetite=0.5),
        "a2": ActorState(id="a2", name="B", cash=75000.0, risk_appetite=0.7),
    }
    manager = ActorManager()
    events = manager.step(state, tick=1)
    assert len(events) == 2
    assert all(e["type"] == "actor_step" for e in events)


def test_step_with_no_actors_returns_empty():
    state = SimulationState()
    manager = ActorManager()
    events = manager.step(state, tick=1)
    assert events == []
