"""
In-process message bus replacing file-based IPC.

GameBus is passed to SimulationKernel, PlayerChoiceEngine, and create_app.
When a bus is provided every component uses threading primitives instead of
the filesystem, which is unreliable inside HF Spaces Docker containers.
"""

import threading
import time


class GameBus:
    def __init__(self):
        self._ready     = threading.Event()
        self._state     = {}
        self._state_lock = threading.Lock()
        self._action    = None
        self._action_ev = threading.Event()
        self._action_lock = threading.Lock()
        self._restart     = threading.Event()
        self._game_active = False
        self._player_name = "You"
        self._last_poll   = None
        self._poll_lock   = threading.Lock()

    # ── Ready handshake ──────────────────────────────────────────────────────

    def signal_ready(self):
        self._ready.set()

    def wait_ready(self, timeout=None):
        self._ready.wait(timeout=timeout)
        self._ready.clear()

    # ── Turn state (kernel → dashboard) ─────────────────────────────────────

    def set_state(self, data):
        with self._state_lock:
            self._state = data

    def get_state(self):
        with self._state_lock:
            return dict(self._state)

    def record_poll(self):
        with self._poll_lock:
            self._last_poll = time.monotonic()

    def reset_poll(self):
        with self._poll_lock:
            self._last_poll = None

    def is_client_connected(self, timeout=10):
        with self._poll_lock:
            if self._last_poll is None:
                return True  # startup grace — no poll yet but game just started
            return (time.monotonic() - self._last_poll) < timeout

    # ── Player action (browser → kernel) ────────────────────────────────────

    def submit_action(self, action, property_id, ltv, bid_premium=0.0):
        with self._action_lock:
            self._action = {
                "action": action, "property_id": property_id,
                "ltv": ltv, "bid_premium": bid_premium,
            }
        self._action_ev.set()

    def wait_action(self, timeout=60):
        self._action_ev.wait(timeout=timeout)
        self._action_ev.clear()

    def has_action(self):
        with self._action_lock:
            return self._action is not None

    def pop_action(self):
        with self._action_lock:
            result = self._action or {"action": "hold", "property_id": None, "ltv": 0.0, "bid_premium": 0.0}
            self._action = None
        return result

    # ── Restart (new player mid-game) ────────────────────────────────────────

    def signal_restart(self):
        self._restart.set()

    def restart_requested(self):
        return self._restart.is_set()

    def clear_restart(self):
        self._restart.clear()

    def reset_for_new_game(self):
        with self._action_lock:
            self._action = None
        self._action_ev.clear()
        with self._poll_lock:
            self._last_poll = None

    # ── Game active lock ─────────────────────────────────────────────────────

    def set_game_active(self, active: bool):
        self._game_active = active

    def is_game_active(self):
        return self._game_active

    # ── Player name ──────────────────────────────────────────────────────────

    def set_player_name(self, name: str):
        self._player_name = (name or "You").strip()[:30]

    def get_player_name(self):
        return self._player_name
