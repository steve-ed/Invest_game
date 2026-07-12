# Multi-Instance Game Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow multiple players to run independent simultaneous game sessions, each identified by a unique game ID in the URL.

**Architecture:** Each player visits `/` which redirects to `/game/{game_id}` (a fresh 8-char hex UUID). The server immediately creates an isolated `GameBus` + `SimulationKernel` thread for that game_id. All API routes are namespaced under `/game/{game_id}/`. The dashboard JS reads the game_id from `window.location.pathname` and passes it in every fetch. Sessions are cleaned up automatically when the game ends or the player disconnects.

**Tech Stack:** Python/Flask, threading, JavaScript (vanilla), existing `GameBus` and `SimulationKernel` (unchanged).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `session_manager.py` | **Create** | `SessionManager`: create/get/destroy per-game `GameBus`+thread |
| `wsgi.py` | **Modify** | Replace global bus+loop with `SessionManager`; create session on page load |
| `visualisation/dashboard_server.py` | **Modify** | Add `/game/<game_id>/state|action|ready` routes; `GET /` redirects to new game_id |
| `static/dashboard.html` | **Modify** | Read game_id from URL; prefix all fetches with `/game/{game_id}/`; add Play Again button |

`GameBus`, `kernel.py`, `player_log.py` — **unchanged**.

---

## Task 1: SessionManager

**Files:**
- Create: `session_manager.py`

- [ ] **Step 1: Create `session_manager.py`**

```python
import threading
import time
import uuid

from game_bus import GameBus
from kernel import SimulationKernel


class SessionManager:
    def __init__(self):
        self._sessions = {}          # game_id -> {"bus": GameBus, "thread": Thread}
        self._lock = threading.Lock()

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
        try:
            bus.reset_for_new_game()
            bus.set_player_name("You")
            kernel = SimulationKernel(turns=20, bus=bus)
            result = kernel.run()
            if result and not result.get("restarted") and not result.get("aborted"):
                self._log(result, bus.get_player_name())
        except Exception as e:
            print(f"[{game_id}] Game loop error: {e}", flush=True)
        finally:
            bus.set_game_active(False)
            bus.set_state({"state": "ended"})
            with self._lock:
                self._sessions.pop(game_id, None)
            print(f"[{game_id}] Session cleaned up.", flush=True)

    @staticmethod
    def _log(result, player_name):
        try:
            import player_log
            lb = result.get("leaderboard", [])
            player_entry = next(
                (e for e in lb if e.get("actor_id") == "player"), None
            )
            if not player_entry or player_name == "You":
                return
            rank = next(
                (i + 1 for i, e in enumerate(lb) if e.get("actor_id") == "player"),
                None,
            )
            player_log.append_result(
                name=player_name,
                score=player_entry["final_score"],
                rank=rank,
                era=result.get("era_label", ""),
                start_year=result.get("start_year", ""),
            )
        except Exception as e:
            print(f"Log result error: {e}", flush=True)

    def new_game_id(self) -> str:
        return uuid.uuid4().hex[:8]
```

- [ ] **Step 2: Verify import works**

```bash
cd C:\Users\steve\projects\RealEstGame
python -c "from session_manager import SessionManager; sm = SessionManager(); print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add session_manager.py
git commit -m "feat: add SessionManager for per-game bus/kernel lifecycle"
```

---

## Task 2: Update dashboard_server.py

**Files:**
- Modify: `visualisation/dashboard_server.py`

Replace the single-bus route setup with session-aware routes under `/game/<game_id>/`. Keep `/players`. Add `GET /` redirect and `GET /game/<game_id>` page-load that creates the session.

- [ ] **Step 1: Rewrite `create_app` in `dashboard_server.py`**

Replace the entire file content with:

```python
import json
import logging
import os
import socket
import threading
import uuid
from flask import Flask, Response, redirect, send_file, request

logging.getLogger("werkzeug").setLevel(logging.ERROR)

_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")


def create_app(session_manager=None, bus=None, state_path=None, action_path=None, ready_path=None):
    """
    session_manager: SessionManager instance (multi-game production mode)
    bus: legacy single GameBus (kept for local dev / file-based fallback)
    """
    app = Flask(__name__, static_folder=_static_dir)

    # ── Multi-game routes ────────────────────────────────────────────────────

    @app.route("/")
    def index():
        if session_manager:
            game_id = session_manager.new_game_id()
            return redirect(f"/game/{game_id}")
        # Legacy: serve dashboard directly
        return send_file(os.path.join(_static_dir, "dashboard.html"))

    @app.route("/game/<game_id>")
    def game_page(game_id):
        if session_manager:
            session_manager.create(game_id)
        return send_file(os.path.join(_static_dir, "dashboard.html"))

    @app.route("/game/<game_id>/state")
    def game_state(game_id):
        b = session_manager.get(game_id) if session_manager else bus
        if b is None:
            return Response("{}", mimetype="application/json",
                            headers={"Access-Control-Allow-Origin": "*"})
        b.record_poll()
        data = json.dumps(b.get_state())
        return Response(data, mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/game/<game_id>/action", methods=["POST"])
    def game_action(game_id):
        b = session_manager.get(game_id) if session_manager else bus
        if b is None:
            return Response('{"ok":false}', mimetype="application/json",
                            headers={"Access-Control-Allow-Origin": "*"})
        payload = request.get_json(silent=True) or {}
        b.submit_action(
            payload.get("action", "hold"),
            payload.get("property_id"),
            float(payload.get("ltv", 0)),
        )
        return Response('{"ok":true}', mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/game/<game_id>/ready", methods=["POST"])
    def game_ready(game_id):
        b = session_manager.get(game_id) if session_manager else bus
        if b is None:
            return Response('{"ok":false}', mimetype="application/json",
                            headers={"Access-Control-Allow-Origin": "*"})
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()[:30]
        if name:
            b.set_player_name(name)
        b.set_game_active(True)
        b.signal_ready()
        return Response('{"ok":true}', mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    # ── Legacy single-bus routes (kept for local/file-based dev) ─────────────

    @app.route("/state")
    def state():
        if bus is not None:
            bus.record_poll()
            data = json.dumps(bus.get_state())
        else:
            try:
                _sp = state_path or os.path.join(os.path.dirname(__file__), "turn_state.json")
                with open(_sp, encoding="utf-8") as f:
                    data = f.read()
            except FileNotFoundError:
                data = "{}"
        return Response(data, mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/action", methods=["POST"])
    def action():
        payload = request.get_json(silent=True) or {}
        if bus is not None:
            bus.submit_action(
                payload.get("action", "hold"),
                payload.get("property_id"),
                float(payload.get("ltv", 0)),
            )
        return Response('{"ok":true}', mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/ready", methods=["POST"])
    def ready():
        if bus is not None:
            if bus.is_game_active():
                s = bus.get_state()
                import json as _j
                return Response(
                    _j.dumps({"ok": False, "waiting": True,
                               "tick": s.get("tick", 0), "total": s.get("total_ticks", 20)}),
                    mimetype="application/json",
                    headers={"Access-Control-Allow-Origin": "*"},
                )
            payload = request.get_json(silent=True) or {}
            name = (payload.get("name") or "").strip()[:30]
            if name:
                bus.set_player_name(name)
            bus.set_game_active(True)
            bus.signal_ready()
        return Response('{"ok":true}', mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/players")
    def players():
        try:
            import player_log
            data = player_log.get_all()
        except Exception:
            data = []
        return Response(json.dumps(data), mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    return app


def _find_port(start=5050, end=5059):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def start_server(state_path=None, bus=None):
    app = create_app(bus=bus, state_path=state_path)
    port = _find_port()
    print(f"Dashboard: http://localhost:{port}", flush=True)
    t = threading.Thread(target=lambda: app.run(port=port, use_reloader=False), daemon=True)
    t.start()
    return port
```

- [ ] **Step 2: Verify import**

```bash
python -c "from visualisation.dashboard_server import create_app; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add visualisation/dashboard_server.py
git commit -m "feat: add per-game-id routes to dashboard_server"
```

---

## Task 3: Update wsgi.py

**Files:**
- Modify: `wsgi.py`

Replace the single-bus game loop with `SessionManager`. The session manager handles all game lifecycle — `wsgi.py` just wires it up.

- [ ] **Step 1: Rewrite `wsgi.py`**

```python
from session_manager import SessionManager
from visualisation.dashboard_server import create_app

session_manager = SessionManager()
app = create_app(session_manager=session_manager)
```

That's the entire file.

- [ ] **Step 2: Verify gunicorn can load it**

```bash
python -c "import wsgi; print('app:', wsgi.app)"
```
Expected: `app: <Flask 'dashboard_server'>`

- [ ] **Step 3: Commit**

```bash
git add wsgi.py
git commit -m "feat: replace single-bus game loop with SessionManager in wsgi.py"
```

---

## Task 4: Update dashboard.html — API routing

**Files:**
- Modify: `static/dashboard.html`

Extract `game_id` from the URL path and prefix all fetch calls. Also handle the `ended` state.

- [ ] **Step 1: Add game_id extraction near the top of the `<script>` block**

Find the line with `let lastTick = 0;` (or similar early JS variable) and add above it:

```javascript
// Extract game_id from /game/{game_id} URL; fall back to legacy routes if not present
const _gameId = (window.location.pathname.match(/^\/game\/([^/]+)/) || [])[1] || null;
const _api = _gameId ? `/game/${_gameId}` : '';
```

- [ ] **Step 2: Update `poll()` fetch URL**

Find:
```javascript
const resp = await fetch("/state?" + Date.now());
```
Replace with:
```javascript
const resp = await fetch(`${_api}/state?` + Date.now());
```

- [ ] **Step 3: Update `loadIntroOpponents()` fetch URL**

Find:
```javascript
const resp = await fetch("/state?" + Date.now());
```
in the `loadIntroOpponents` / `waitForIntro` function. Replace with:
```javascript
const resp = await fetch(`${_api}/state?` + Date.now());
```

- [ ] **Step 4: Update `startGame()` fetch URL**

Find:
```javascript
const resp = await fetch("/ready", {
```
Replace with:
```javascript
const resp = await fetch(`${_api}/ready`, {
```

- [ ] **Step 5: Update `submitAction()` fetch URL**

Find:
```javascript
fetch('/action', {
```
Replace with:
```javascript
fetch(`${_api}/action`, {
```

- [ ] **Step 6: Handle `state === "ended"` in `poll()`**

In `poll()`, after the existing `if (d.state === "intro")` check, add:

```javascript
if (d.state === "ended") { showGameEnded(); return; }
```

Then add the `showGameEnded` function (place it near `showEraBanner`):

```javascript
function showGameEnded() {
  hideActionBar();
  document.getElementById("main-area").style.display = "none";
  const banner = document.getElementById("era-banner");
  banner.style.display = "flex";
  banner.style.flexDirection = "column";
  banner.style.paddingBottom = "80px";
  document.getElementById("era-title").textContent = "Game Over";
  document.getElementById("era-sub").textContent = "The game has ended. Play again?";
  // Reuse the play-again button added in Task 5
}
```

- [ ] **Step 7: Commit**

```bash
git add static/dashboard.html
git commit -m "feat: route dashboard API calls through /game/{game_id} prefix"
```

---

## Task 5: Add "Play Again" button to game-over screen

**Files:**
- Modify: `static/dashboard.html`

After a game ends the player should be able to start a new session cleanly.

- [ ] **Step 1: Find the game-over banner HTML**

Locate the `<div id="era-banner"` element. Inside it, find where the leaderboard table ends (after `<div id="leaderboard-table"></div>`). Add a Play Again button:

```html
<div style="text-align:center;margin-top:32px;padding-bottom:40px;">
  <button onclick="location.href='/'" style="
    padding:14px 40px;font-size:15px;font-weight:700;letter-spacing:1px;
    background:#032147;color:#209dd7;border:2px solid #209dd7;
    border-radius:6px;cursor:pointer;text-transform:uppercase;">
    Play Again
  </button>
</div>
```

- [ ] **Step 2: Verify the button appears after a game ends in local testing**

Run locally with `python main.py`, complete a game, confirm the button renders and clicking it navigates to `/`.

- [ ] **Step 3: Commit**

```bash
git add static/dashboard.html
git commit -m "feat: add Play Again button to game-over screen"
```

---

## Task 6: Push and deploy

- [ ] **Step 1: Push branch to GitHub**

```bash
git push -u origin multi
```

- [ ] **Step 2: Push to Hugging Face**

```bash
git push space multi:main
```

- [ ] **Step 3: Verify on HF Space**

1. Open the HF Space URL — should redirect from `/` to `/game/{id}`
2. Open the same Space in a second browser tab — should get a *different* game_id and run independently
3. Both games should run simultaneously without interfering
4. Both leaderboard entries should appear in `/players`

---

## Self-Review

**Spec coverage:**
- ✅ Multiple simultaneous sessions — `SessionManager` + per-game routes
- ✅ Session isolation — each `GameBus` is independent
- ✅ URL-based game IDs — `/game/{game_id}` path
- ✅ Session cleanup on game end — `finally` block in `_run_game`
- ✅ Session cleanup on disconnect — existing `is_client_connected` mechanism aborts the kernel, `finally` cleans up
- ✅ Legacy single-bus routes preserved — `main.py` local dev unaffected
- ✅ Leaderboard shared — `/players` unchanged
- ✅ Play Again flow — button navigates to `/`, gets fresh game_id

**Known limitations not in scope:**
- No max concurrent session limit (low risk on HF free tier for now)
- Session not pre-warmed on `/` visit — kernel starts on `GET /game/{id}`, which is the redirect target, so it's instant
- `wait_ready` has no timeout — a player who opens the page but never clicks Start leaves a kernel thread blocked indefinitely. Acceptable for now; add `wait_ready(timeout=300)` later if needed.
