import json
import os
import tempfile
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    state_path = tmp_path / "turn_state.json"
    state_path.write_text(json.dumps({
        "tick": 3,
        "total_ticks": 20,
        "mode": "student",
        "macro_history": [],
        "wealth_history": [],
        "current_events": [],
        "actors": {},
        "x_labels": [],
        "era_label": None,
        "scenario": "baseline",
    }))
    monkeypatch.setenv("TURN_STATE_PATH", str(state_path))
    from visualisation.dashboard_server import create_app
    app = create_app(state_path=str(state_path))
    app.config["TESTING"] = True
    return app.test_client()


def test_state_endpoint_returns_json(client):
    resp = client.get("/state")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["tick"] == 3


def test_state_endpoint_has_cors_header(client):
    resp = client.get("/state")
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_root_returns_html(client):
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"<html" in resp.data.lower() or b"<!doctype" in resp.data.lower()
