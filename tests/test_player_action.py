import json
import pytest
from player.choices import PlayerChoiceEngine
from state import Property, ActorState, SimulationState, MacroState


def _make_state():
    prop = Property(id="px", region="Test", base_value=200_000,
                    current_value=200_000, rent=900.0)
    actor = ActorState(id="player", name="Player", cash=250_000,
                       risk_appetite=0.5, portfolio=["p1"])
    owned_prop = Property(id="p1", region="London", base_value=300_000,
                          current_value=300_000, rent=1500.0)
    state = SimulationState()
    state.macro = MacroState()
    state.properties = [prop, owned_prop]
    state.actors = {"player": actor}
    return state


def test_player_defaults_to_hold_when_no_action_file(tmp_path, monkeypatch):
    monkeypatch.setattr("player.choices.ACTION_PATH", str(tmp_path / "action.json"))
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=1)
    assert events[0]["action"] == "hold"


def test_player_reads_buy_action_for_current_tick(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 1, "action": "buy", "property_id": "px"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=1)
    assert events[0]["action"] == "buy"
    assert events[0]["property_id"] == "px"


def test_player_ignores_stale_action(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 1, "action": "buy", "property_id": "px"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=2)   # stale — tick doesn't match
    assert events[0]["action"] == "hold"


def test_player_reads_sell_action(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 3, "action": "sell", "property_id": "p1"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=3)
    assert events[0]["action"] == "sell"
    assert events[0]["property_id"] == "p1"


def test_action_file_cleared_after_read(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 1, "action": "buy", "property_id": "px"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    engine.step(state, tick=1)
    # second call same tick should hold (file cleared)
    events = engine.step(state, tick=1)
    assert events[0]["action"] == "hold"
