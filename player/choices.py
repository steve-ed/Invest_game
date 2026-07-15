import json
import os

ACTION_PATH = os.path.join(os.path.dirname(__file__), "..", "visualisation", "player_action.json")


class PlayerChoiceEngine:
    def __init__(self, bus=None):
        self._bus = bus

    def step(self, state, tick):
        action, property_id, ltv, bid_premium = self._read_action()
        return [{
            "type": "player_action",
            "tick": tick,
            "actor_id": "player",
            "action": action,
            "property_id": property_id,
            "ltv": ltv,
            "bid_premium": bid_premium,
            "detail": f"Player: {action}{' ' + property_id if property_id else ''}",
        }]

    def _read_action(self):
        if self._bus is not None:
            result = self._bus.pop_action()
            return (result["action"], result.get("property_id"),
                    float(result.get("ltv", 0)), float(result.get("bid_premium", 0)))

        try:
            with open(ACTION_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("action"):
                with open(ACTION_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                return (data.get("action", "hold"), data.get("property_id"),
                        float(data.get("ltv", 0)), float(data.get("bid_premium", 0)))
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return "hold", None, 0.0, 0.0
