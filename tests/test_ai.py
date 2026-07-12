from state import SimulationState, ActorState, Property
from ai import AIController


def _state_with_ai_actor(cash=100000.0, risk_appetite=0.6):
    state = SimulationState()
    state.actors = {
        "ai1": ActorState(id="ai1", name="AI Investor", cash=cash, risk_appetite=risk_appetite),
    }
    # unowned property available on the market
    state.properties = [
        Property(id="p99", region="Test", base_value=80000.0, current_value=80000.0, rent=500.0)
    ]
    return state


def test_hold_when_interest_rate_is_high():
    state = _state_with_ai_actor()
    state.macro.interest_rate = 0.09  # above HIGH_RATE_THRESHOLD of 0.07
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "hold"


def test_buy_when_price_low_and_cash_sufficient_and_risk_tolerant():
    # yield strategy: rent 500/month on 80k → yield=7.5% > 6%, rate 5% <= 7%
    state = _state_with_ai_actor(cash=100000.0, risk_appetite=0.8)
    state.actors["ai1"].strategy = "yield"
    state.macro.interest_rate = 0.05
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "buy"


def test_no_buy_when_risk_appetite_low():
    state = _state_with_ai_actor(cash=100000.0, risk_appetite=0.3)
    state.macro.price_index = 90.0
    state.macro.interest_rate = 0.05
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "hold"


def test_sell_when_price_high_and_has_portfolio():
    # leverage strategy: rate 9% > LEVERAGE_SELL_RATE 8.5% → sell
    state = _state_with_ai_actor()
    state.actors["ai1"].strategy = "leverage"
    state.actors["ai1"].portfolio = ["p1"]
    state.macro.interest_rate = 0.09
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "sell"


def test_step_returns_event_per_ai_actor():
    state = SimulationState()
    state.actors = {
        "ai1": ActorState(id="ai1", name="AI", cash=50000.0, risk_appetite=0.5),
        "ai2": ActorState(id="ai2", name="AI2", cash=60000.0, risk_appetite=0.4),
    }
    controller = AIController()
    events = controller.step(state, tick=1)
    assert len(events) == 2
    assert all(e["type"] == "ai_action" for e in events)


def test_player_actor_is_skipped():
    state = SimulationState()
    state.actors = {
        "player": ActorState(id="player", name="Player", cash=80000.0, risk_appetite=0.5),
        "ai1": ActorState(id="ai1", name="AI", cash=50000.0, risk_appetite=0.5),
    }
    controller = AIController()
    events = controller.step(state, tick=1)
    assert len(events) == 1
    assert events[0]["actor_id"] == "ai1"
