import pytest
from ai import AIController
from state import Property, ActorState, SimulationState, MacroState


def _make_state(rate=0.05, price_index=100.0, rent_growth=0.03):
    state = SimulationState()
    state.macro = MacroState(price_index=price_index, interest_rate=rate,
                              rent_growth=rent_growth)
    return state


def _prop(pid, value, rent, epc_band=4):
    return Property(id=pid, region="Test", base_value=value,
                    current_value=value, rent=rent, epc_band=epc_band)


def test_yield_ai_buys_high_yield_property_at_low_rate():
    state = _make_state(rate=0.05)
    # rent=1200/month → annual=14400 → yield=14400/200000=7.2% > 6%
    available = [_prop("px", 200_000, 1_200)]
    actor = ActorState(id="ai1", name="Conservative AI", cash=300_000,
                       risk_appetite=0.3, strategy="yield")
    state.actors = {"ai1": actor}
    state.properties = available
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "buy"
    assert pid == "px"
    assert ltv == pytest.approx(0.35)  # yield AI buys with low LTV


def test_yield_ai_holds_when_rate_high():
    state = _make_state(rate=0.08)
    available = [_prop("px", 200_000, 1_200)]
    actor = ActorState(id="ai1", name="Conservative AI", cash=300_000,
                       risk_appetite=0.3, strategy="yield")
    state.actors = {"ai1": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "hold"


def test_yield_ai_holds_when_yield_too_low():
    state = _make_state(rate=0.05)
    # rent=500/month → annual=6000 → yield=6000/200000=3% < 6%
    available = [_prop("px", 200_000, 500)]
    actor = ActorState(id="ai1", name="Conservative AI", cash=300_000,
                       risk_appetite=0.3, strategy="yield")
    state.actors = {"ai1": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "hold"


def test_leverage_ai_buys_with_75pct_ltv_at_low_rate():
    state = _make_state(rate=0.04)
    available = [_prop("px", 200_000, 800)]
    actor = ActorState(id="ai2", name="Aggressive AI", cash=100_000,
                       risk_appetite=0.9, strategy="leverage", portfolio=[])
    state.actors = {"ai2": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "buy"
    assert ltv == pytest.approx(0.75)


def test_leverage_ai_sells_on_rate_spike():
    state = _make_state(rate=0.09)
    actor = ActorState(id="ai2", name="Aggressive AI", cash=50_000,
                       risk_appetite=0.9, strategy="leverage", portfolio=["p01"])
    prop_owned = _prop("p01", 300_000, 900, epc_band=1)
    state.actors = {"ai2": actor}
    state.properties = [prop_owned]
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, [])
    assert action == "sell"
    assert pid == "p01"


def test_balanced_ai_holds_by_default():
    state = _make_state(rate=0.06)
    actor = ActorState(id="player", name="Player", cash=100_000,
                       risk_appetite=0.5, strategy="balanced")
    state.actors = {"player": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, [])
    assert action == "hold"
