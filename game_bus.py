"""
In-process message bus replacing file-based IPC.

GameBus is passed to SimulationKernel, PlayerChoiceEngine, and create_app.
When a bus is provided every component uses threading primitives instead of
the filesystem, which is unreliable inside HF Spaces Docker containers.
"""

import collections
import threading
import time


class GameBus:
    def __init__(self):
        self._ready      = threading.Event()
        self._state      = {}
        self._state_lock = threading.Lock()

        # Action queue — a deque so rapid double-POSTs don't overwrite each other.
        # The kernel pops one action per tick.
        self._action_queue      = collections.deque()
        self._action_queue_lock = threading.Lock()
        self._action_ev         = threading.Event()

        self._restart      = threading.Event()
        self._game_active  = False
        self._game_active_lock = threading.Lock()
        self._player_name  = "You"
        self._player_name_lock = threading.Lock()
        self._tax_mode     = "none"
        self._tax_mode_lock = threading.Lock()
        self._last_poll    = None
        self._poll_lock    = threading.Lock()

    # ── Ready handshake ──────────────────────────────────────────────────────

    def signal_ready(self):
        self._ready.set()

    def wait_ready(self, timeout=300):
        """Block until signal_ready() is called. Returns True if signalled, False on timeout."""
        signalled = self._ready.wait(timeout=timeout)
        self._ready.clear()
        return signalled

    # ── Turn state (kernel → dashboard) ─────────────────────────────────────

    def set_state(self, data):
        with self._state_lock:
            self._state = data

    def get_state(self):
        # Return a deep copy so callers can't mutate shared nested objects.
        # json round-trip is faster than copy.deepcopy for plain dicts.
        import json
        with self._state_lock:
            return json.loads(json.dumps(self._state))

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
        with self._action_queue_lock:
            self._action_queue.append({
                "action": action, "property_id": property_id,
                "ltv": ltv, "bid_premium": bid_premium,
            })
        self._action_ev.set()

    def wait_action(self, timeout=60):
        """Block until an action is queued. Does NOT clear the event (pop_action does)."""
        self._action_ev.wait(timeout=timeout)

    def has_action(self):
        with self._action_queue_lock:
            return len(self._action_queue) > 0

    def pop_action(self):
        with self._action_queue_lock:
            if self._action_queue:
                result = self._action_queue.popleft()
            else:
                result = {"action": "hold", "property_id": None, "ltv": 0.0, "bid_premium": 0.0}
            if not self._action_queue:
                self._action_ev.clear()  # clear only when queue is empty
        return result

    # ── Restart (new player mid-game) ────────────────────────────────────────

    def signal_restart(self):
        self._restart.set()

    def wait_restart(self):
        """Block until player signals ready for a new game."""
        self._restart.wait()
        self._restart.clear()

    def restart_requested(self):
        return self._restart.is_set()

    def clear_restart(self):
        self._restart.clear()

    def reset_for_new_game(self):
        with self._action_queue_lock:
            self._action_queue.clear()
            self._action_ev.clear()  # inside the lock so no submit_action can race
        with self._poll_lock:
            self._last_poll = None

    # ── Game active lock ─────────────────────────────────────────────────────

    def set_game_active(self, active: bool):
        with self._game_active_lock:
            self._game_active = active

    def is_game_active(self):
        with self._game_active_lock:
            return self._game_active

    # ── Player name ──────────────────────────────────────────────────────────

    def set_player_name(self, name: str):
        with self._player_name_lock:
            self._player_name = (name or "You").strip()[:30]

    def get_player_name(self):
        with self._player_name_lock:
            return self._player_name

    # ── Tax mode ─────────────────────────────────────────────────────────────

    def set_tax_mode(self, mode: str):
        _valid = {"none", "basic", "higher", "company"}
        with self._tax_mode_lock:
            self._tax_mode = mode if mode in _valid else "none"

    def get_tax_mode(self):
        with self._tax_mode_lock:
            return self._tax_mode
