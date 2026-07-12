import pytest
from kernel import SimulationKernel, _calculate_sdlt, _epc_upgrade_cost
from state import Property, ActorState, SimulationState, MacroState


def test_sdlt_zero_below_125k():
    assert _calculate_sdlt(100_000) == pytest.approx(3_000)   # 3% surcharge only


def test_sdlt_at_250k():
    # 125k @ 3% = 3750, 125k @ 5% = 6250 → total 10000
    assert _calculate_sdlt(250_000) == pytest.approx(10_000)


def test_sdlt_at_500k():
    # 125k@3%=3750, 125k@5%=6250, 250k@8%=20000 → 30000
    assert _calculate_sdlt(500_000) == pytest.approx(30_000)


def test_epc_upgrade_cost_band_4():
    assert _epc_upgrade_cost(4) == 5_000   # D→C


def test_epc_upgrade_cost_band_5():
    assert _epc_upgrade_cost(5) == 12_000  # E→C


def test_epc_upgrade_cost_band_6():
    assert _epc_upgrade_cost(6) == 20_000  # F→C


def test_epc_upgrade_cost_band_7():
    assert _epc_upgrade_cost(7) == 30_000  # G→C


def _make_buy_state(price=200_000, cash=300_000, ltv=0.0):
    prop = Property(id="px", region="Test", base_value=price,
                    current_value=price, rent=800.0, epc_band=4)
    actor = ActorState(id="a1", name="Inv", cash=cash, risk_appetite=0.5)
    state = SimulationState()
    state.macro = MacroState(price_index=100.0, interest_rate=0.05, rent_growth=0.03)
    state.properties = [prop]
    state.actors = {"a1": actor}
    return state, prop, actor


def test_buy_deducts_sdlt():
    state, prop, actor = _make_buy_state(price=200_000, cash=300_000)
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "buy", "property_id": "px",
                        "ltv": 0.0})
    sdlt = _calculate_sdlt(200_000)
    expected_cash = 300_000 - 200_000 - sdlt
    assert actor.cash == pytest.approx(expected_cash, rel=1e-3)


def test_buy_sets_void_period():
    state, prop, actor = _make_buy_state(price=200_000, cash=300_000)
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "buy", "property_id": "px",
                        "ltv": 0.0})
    assert prop.void_ticks_remaining == 1


def test_buy_with_mortgage_sets_balance():
    state, prop, actor = _make_buy_state(price=200_000, cash=300_000)
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "buy", "property_id": "px",
                        "ltv": 0.75})
    assert prop.mortgage_balance == pytest.approx(150_000)
    deposit = 200_000 * 0.25
    sdlt = _calculate_sdlt(200_000)
    assert actor.cash == pytest.approx(300_000 - deposit - sdlt, rel=1e-3)


def test_sell_deducts_agent_fee_and_repays_mortgage():
    state, prop, actor = _make_buy_state(price=200_000, cash=10_000)
    prop.mortgage_balance = 120_000
    actor.portfolio = ["px"]
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "sell", "property_id": "px"})
    agent_fee = 200_000 * 0.015
    net = 200_000 - 120_000 - agent_fee
    assert actor.cash == pytest.approx(10_000 + net, rel=1e-3)
    assert "px" not in actor.portfolio


def test_upgrade_reduces_epc_band_and_deducts_cost():
    state, prop, actor = _make_buy_state(price=200_000, cash=50_000)
    prop.epc_band = 5
    actor.portfolio = ["px"]
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "upgrade", "property_id": "px"})
    assert prop.epc_band == 3        # E→C (two bands improvement)
    cost = _epc_upgrade_cost(5)
    assert actor.cash == pytest.approx(50_000 - cost, rel=1e-3)
    assert actor.total_transaction_costs == pytest.approx(cost, rel=1e-3)
