import pytest
from state import Property, ActorState, SimulationState, MacroState
from actors import ActorManager


def _make_state(interest_rate=0.05, rent_growth=0.03):
    prop = Property(id="p1", region="London", base_value=300000.0,
                    current_value=300000.0, rent=1500.0)
    actor = ActorState(id="a1", name="Inv", cash=50000.0, risk_appetite=0.5,
                       portfolio=["p1"])
    state = SimulationState()
    state.macro = MacroState(price_index=100.0, interest_rate=interest_rate,
                             rent_growth=rent_growth)
    state.properties = [prop]
    state.actors = {"a1": actor}
    return state, prop, actor


def _savings(cash, rate):
    """Semi-annual savings interest at 30% of BoE rate."""
    return cash * rate * 0.3 / 2


def test_rent_collected_each_tick():
    state, prop, actor = _make_state()
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    # savings interest + rent income
    expected = initial_cash + _savings(initial_cash, 0.05) + 1500 * 6
    assert actor.cash == pytest.approx(expected, rel=1e-6)


def test_rent_accumulates_on_actor():
    state, prop, actor = _make_state()
    mgr = ActorManager()
    mgr.step(state, tick=1)
    assert actor.total_rent_received == pytest.approx(9000, rel=1e-3)


def test_void_period_suppresses_rent():
    state, prop, actor = _make_state()
    prop.void_ticks_remaining = 1
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    expected = initial_cash + _savings(initial_cash, 0.05)
    assert actor.cash == pytest.approx(expected, rel=1e-6)
    assert prop.void_ticks_remaining == 0


def test_void_decrements_each_tick():
    state, prop, actor = _make_state()
    prop.void_ticks_remaining = 2
    mgr = ActorManager()
    mgr.step(state, tick=1)
    assert prop.void_ticks_remaining == 1


def test_mortgage_interest_deducted_semi_annually():
    state, prop, actor = _make_state(interest_rate=0.06)
    prop.mortgage_balance = 200000.0
    prop.mortgage_rate = 0.06
    prop.is_fixed_rate = True
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    # savings on initial cash, then mortgage deducted, then rent
    savings = _savings(initial_cash, 0.06)
    interest = 200000.0 * 0.06 / 2  # 6000
    rent = 1500 * 6                  # 9000
    expected = initial_cash + savings - interest + rent
    assert actor.cash == pytest.approx(expected, rel=1e-6)


def test_mortgage_uses_variable_rate_when_not_fixed():
    state, prop, actor = _make_state(interest_rate=0.08)
    prop.mortgage_balance = 100000.0
    prop.mortgage_rate = 0.05   # ignored when is_fixed_rate=False
    prop.is_fixed_rate = False
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    savings = _savings(initial_cash, 0.08)
    interest = 100000.0 * 0.08 / 2  # 4000
    rent = 1500 * 6                  # 9000
    expected = initial_cash + savings - interest + rent
    assert actor.cash == pytest.approx(expected, rel=1e-6)


def test_mortgage_paid_accumulates():
    state, prop, actor = _make_state(interest_rate=0.06)
    prop.mortgage_balance = 200000.0
    prop.mortgage_rate = 0.06
    prop.is_fixed_rate = True
    mgr = ActorManager()
    mgr.step(state, tick=1)
    assert actor.total_mortgage_paid == pytest.approx(6000, rel=1e-2)
