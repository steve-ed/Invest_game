import threading
import uuid

from game_bus import GameBus
from kernel import SimulationKernel


class SessionManager:
    def __init__(self):
        self._sessions = {}          # game_id -> {"bus": GameBus, "thread": Thread}
        self._lock = threading.Lock()

    def new_game_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def create(self, game_id: str) -> GameBus:
        """Create a new game session and start its kernel thread. Idempotent."""
        with self._lock:
            if game_id in self._sessions:
                return self._sessions[game_id]["bus"]
            bus = GameBus()
            t = threading.Thread(
                target=self._run_game, args=(game_id, bus), daemon=True
            )
            self._sessions[game_id] = {"bus": bus, "thread": t}
            t.start()
            return bus

    def get(self, game_id: str):
        """Return the GameBus for game_id, or None if not found."""
        with self._lock:
            s = self._sessions.get(game_id)
            return s["bus"] if s else None

    def _run_game(self, game_id: str, bus: GameBus):
        result = None
        exc = None
        try:
            bus.reset_for_new_game()
            bus.set_player_name("You")
            kernel = SimulationKernel(turns=20, bus=bus)
            result = kernel.run()
            if result and not result.get("restarted") and not result.get("aborted"):
                _log_result(result, bus.get_player_name())
        except Exception as e:
            exc = e
            print(f"[{game_id}] Game loop error: {e}", flush=True)
            # Unblock any Flask handler waiting on the ready or action events so
            # they don't hang forever after the kernel thread dies.
            bus.signal_ready()
            bus.submit_action("hold", None, 0.0)
        finally:
            bus.set_game_active(False)
            bus.set_state({"state": "ended"})
            with self._lock:
                self._sessions.pop(game_id, None)
            print(f"[{game_id}] Session cleaned up.", flush=True)


def _log_result(result, player_name):
    try:
        import player_log
        lb = result.get("leaderboard", [])
        player_entry = next((e for e in lb if e.get("actor_id") == "player"), None)
        if not player_entry or player_name == "You":
            return
        rank = next(
            (i + 1 for i, e in enumerate(lb) if e.get("actor_id") == "player"), None
        )
        player_log.append_result(
            name=player_name,
            score=player_entry["final_score"],
            rank=rank,
            era=result.get("era_label", ""),
            start_year=result.get("start_year", ""),
        )
    except Exception as e:
        print(f"Player log write failed: {e}", flush=True)
