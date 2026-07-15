import pytest
from game_bus import GameBus
from player.choices import PlayerChoiceEngine


def test_submit_action_stores_bid_premium():
    bus = GameBus()
    bus.submit_action("buy", "prop1", 0.75, 0.10)
    result = bus.pop_action()
    assert result["bid_premium"] == 0.10


def test_pop_action_default_bid_premium():
    bus = GameBus()
    result = bus.pop_action()
    assert result["bid_premium"] == 0.0


def test_submit_action_default_bid_premium():
    bus = GameBus()
    bus.submit_action("hold", None, 0.0)
    result = bus.pop_action()
    assert result["bid_premium"] == 0.0


def test_player_choice_engine_passes_bid_premium():
    bus = GameBus()
    bus.submit_action("buy", "prop1", 0.75, 0.05)
    engine = PlayerChoiceEngine(bus=bus)
    events = engine.step(None, 1)
    assert events[0]["bid_premium"] == 0.05


def test_player_choice_engine_default_bid_premium():
    bus = GameBus()
    bus.submit_action("hold", None, 0.0)
    engine = PlayerChoiceEngine(bus=bus)
    events = engine.step(None, 1)
    assert events[0]["bid_premium"] == 0.0


def test_server_route_converts_string_bid_premium():
    from visualisation.dashboard_server import create_app
    bus = GameBus()
    app = create_app(bus=bus)
    client = app.test_client()
    client.post("/action", json={"action": "buy", "property_id": "p1", "ltv": 0.75, "bid_premium": "0.05"})
    result = bus.pop_action()
    assert result["bid_premium"] == pytest.approx(0.05)
