import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from state import SimulationState, Property, ActorState, MacroState
from kernel import SimulationKernel, _MARKET_NATIONAL_BASE, _MARKET_REGION_PROFILES


def _minimal_kernel():
    k = SimulationKernel.__new__(SimulationKernel)
    k.state = SimulationState()
    k.state.macro = MacroState(price_index=100.0, interest_rate=0.05, rent_growth=0.03)
    k.state.actors = {}
    k.state.properties = []
    k._next_market_id = 100
    return k


def test_add_auction_property_sets_is_auction():
    k = _minimal_kernel()
    k._add_auction_property()
    assert any(p.is_auction for p in k.state.properties)


def test_auction_property_is_15_pct_below_market():
    k = _minimal_kernel()
    k._add_auction_property()
    ap = next(p for p in k.state.properties if p.is_auction)
    max_market = _MARKET_NATIONAL_BASE * max(
        p["price_level"] for p in _MARKET_REGION_PROFILES.values()
    ) * 1.3
    assert ap.current_value < max_market * 0.86


def test_auction_property_removed_next_tick_if_unsold():
    k = _minimal_kernel()
    k._add_auction_property()
    assert any(p.is_auction for p in k.state.properties)
    k._remove_stale_auction_properties()
    assert not any(p.is_auction for p in k.state.properties)


def test_auction_property_not_removed_if_owned():
    k = _minimal_kernel()
    k._add_auction_property()
    ap = next(p for p in k.state.properties if p.is_auction)
    actor = ActorState(id="player", name="P", cash=0, risk_appetite=0.5)
    actor.portfolio.append(ap.id)
    k.state.actors["player"] = actor
    k._remove_stale_auction_properties()
    assert ap in k.state.properties


def _kernel_with_auction():
    from ai import AIController
    k = _minimal_kernel()
    k.ai = AIController()
    actor = ActorState(id="player", name="P", cash=200_000, risk_appetite=0.5)
    ai1   = ActorState(id="ai1", name="Conservative", cash=200_000, risk_appetite=0.3, strategy="yield")
    ai2   = ActorState(id="ai2", name="Aggressive",   cash=200_000, risk_appetite=0.8, strategy="capital")
    k.state.actors = {"player": actor, "ai1": ai1, "ai2": ai2}
    prop = Property(
        id="auc001", region="North", base_value=100_000, current_value=100_000,
        rent=500.0, is_auction=True,
    )
    k.state.properties = [prop]
    return k, prop, actor, ai1, ai2


def test_auction_player_wins_when_outbids_aggressive():
    k, prop, actor, ai1, ai2 = _kernel_with_auction()
    k._execute_action({"actor_id": "player", "action": "buy", "property_id": "auc001",
                        "ltv": 0.0, "bid_premium": 0.10})
    assert "auc001" in actor.portfolio


def test_auction_player_loses_when_underbids_aggressive():
    k, prop, actor, ai1, ai2 = _kernel_with_auction()
    k._execute_action({"actor_id": "player", "action": "buy", "property_id": "auc001",
                        "ltv": 0.0, "bid_premium": 0.0})
    assert "auc001" not in actor.portfolio


def test_auction_player_wins_ties_against_aggressive():
    k, prop, actor, ai1, ai2 = _kernel_with_auction()
    k._execute_action({"actor_id": "player", "action": "buy", "property_id": "auc001",
                        "ltv": 0.0, "bid_premium": 0.05})
    assert "auc001" in actor.portfolio


def test_auction_player_pays_their_bid_not_asking():
    k, prop, actor, ai1, ai2 = _kernel_with_auction()
    cash_before = actor.cash
    k._execute_action({"actor_id": "player", "action": "buy", "property_id": "auc001",
                        "ltv": 0.0, "bid_premium": 0.10})
    paid = cash_before - actor.cash
    expected = round(100_000 * 1.10)
    assert paid == expected
