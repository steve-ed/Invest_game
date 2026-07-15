import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from state import SimulationState, Property, ActorState, MacroState
from kernel import SimulationKernel


def _minimal_kernel():
    k = SimulationKernel.__new__(SimulationKernel)
    k.state = SimulationState()
    k.state.macro = MacroState(price_index=100.0, interest_rate=0.05, rent_growth=0.03)
    prop = Property(id="p01", region="North", base_value=100_000, current_value=100_000, rent=500.0)
    actor = ActorState(id="player", name="Player", cash=50_000, risk_appetite=0.5)
    actor.portfolio.append("p01")
    k.state.properties = [prop]
    k.state.actors = {"player": actor}
    return k, prop, actor


def test_renovate_costs_10_pct_of_value():
    k, prop, actor = _minimal_kernel()
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert actor.cash == 50_000 - 10_000  # 10% of 100k


def test_renovate_boosts_rent_15_pct():
    k, prop, actor = _minimal_kernel()
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert abs(prop.rent - 500.0 * 1.15) < 0.01


def test_renovate_boosts_value_8_pct():
    k, prop, actor = _minimal_kernel()
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert abs(prop.current_value - 100_000 * 1.08) < 0.01


def test_renovate_sets_renovated_flag():
    k, prop, actor = _minimal_kernel()
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert prop.renovated is True


def test_renovate_cannot_be_done_twice():
    k, prop, actor = _minimal_kernel()
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    rent_after_first = prop.rent
    cash_after_first = actor.cash
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert prop.rent == rent_after_first
    assert actor.cash == cash_after_first


def test_renovate_blocked_if_insufficient_cash():
    k, prop, actor = _minimal_kernel()
    actor.cash = 5_000  # less than 10% of 100k
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert prop.renovated is False
    assert actor.cash == 5_000


def test_renovate_only_works_on_owned_property():
    k, prop, actor = _minimal_kernel()
    actor.portfolio.clear()
    k._execute_action({"actor_id": "player", "action": "renovate", "property_id": "p01", "ltv": 0})
    assert prop.renovated is False
