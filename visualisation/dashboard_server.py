import json
import logging
import os
import socket
import threading
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
            float(payload.get("bid_premium", 0)),
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
        b.reset_poll()
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
                float(payload.get("bid_premium", 0)),
            )
        return Response('{"ok":true}', mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/ready", methods=["POST"])
    def ready():
        if bus is not None:
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


def start_server(state_path=None, bus=None, port=5051):
    app = create_app(bus=bus, state_path=state_path)
    print(f"Dashboard: http://localhost:{port}", flush=True)
    t = threading.Thread(target=lambda: app.run(port=port, use_reloader=False), daemon=True)
    t.start()
    return port
