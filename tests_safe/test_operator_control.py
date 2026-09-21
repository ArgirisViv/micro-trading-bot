import json

from runtime_control import read_control, write_control
from scripts.paper_trading import multi_asset_loop as trader
from webapp import server
import pandas as pd


def test_missing_or_malformed_control_blocks_entries(tmp_path, monkeypatch):
    path = tmp_path / "control.json"
    monkeypatch.setenv("CONTROL_FILE", str(path))
    assert read_control()["paused"] is True
    assert trader.entries_enabled() is False
    path.write_text('{"paused": "false"}', encoding="utf-8")
    assert read_control()["paused"] is True
    assert trader.entries_enabled() is False


def test_atomic_resume_then_pause_controls_trader(tmp_path, monkeypatch):
    path = tmp_path / "control.json"
    monkeypatch.setenv("CONTROL_FILE", str(path))
    write_control(paused=False)
    assert trader.entries_enabled() is True
    assert json.loads(path.read_text(encoding="utf-8"))["paused"] is False
    write_control(paused=True)
    assert trader.entries_enabled() is False


def test_api_requires_login_and_csrf_for_controls(client):
    unauthenticated = server.app.test_client()
    assert unauthenticated.get("/api/overview").status_code == 401
    assert unauthenticated.get("/api/control").status_code == 401
    assert unauthenticated.post("/api/control", json={"action": "resume"}).status_code == 401

    assert client.get("/api/control").get_json()["paused"] is True
    assert client.post("/api/control", json={"action": "resume"}).status_code == 403
    csrf = client.get("/api/auth/status").get_json()["csrf"]
    headers = {"X-Orbit-CSRF": csrf, "X-Requested-With": "Orbit"}
    assert client.post("/api/control", json={"action": "delete"}, headers=headers).status_code == 400
    assert client.post("/api/control", json={"action": "resume"}, headers=headers).get_json()["paused"] is False
    assert trader.entries_enabled() is True
    assert client.post("/api/control", json={"action": "pause"}, headers=headers).get_json()["paused"] is True
    assert trader.entries_enabled() is False
    assert client.post("/api/auth/logout", json={}, headers=headers).status_code == 200
    assert client.get("/api/control").status_code == 401


def test_wrong_password_cannot_unlock(client):
    unauthenticated = server.app.test_client()
    response = unauthenticated.post("/api/auth/login", json={"password": "wrong-password-123"},
                                    headers={"X-Requested-With": "Orbit"})
    assert response.status_code == 401
    assert unauthenticated.get("/api/auth/status").get_json()["authenticated"] is False


def test_repeated_wrong_passwords_are_throttled(client, monkeypatch):
    monkeypatch.setattr(server, "_login_attempts", server.defaultdict(server.deque))
    unauthenticated = server.app.test_client()
    headers = {"X-Requested-With": "Orbit"}
    for _ in range(5):
        assert unauthenticated.post("/api/auth/login", json={"password": "bad-password"},
                                    headers=headers).status_code == 401
    assert unauthenticated.post("/api/auth/login", json={"password": "correct-horse-paper-123"},
                                headers=headers).status_code == 429


def test_unconfigured_dashboard_fails_closed(client, monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD_HASH")
    unauthenticated = server.app.test_client()
    assert unauthenticated.get("/api/overview").status_code == 503
    assert unauthenticated.post("/api/auth/login", json={"password": "anything"},
                                headers={"X-Requested-With": "Orbit"}).status_code == 503


def test_static_login_and_operator_controls_are_served(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="login-form"' in html
    assert 'id="pause-button"' in html
    assert 'id="resume-button"' in html


def test_paper_equity_history_is_broker_labeled_and_filters_bad_values(client, monkeypatch, tmp_path):
    equity_file = tmp_path / "equity.csv"
    monkeypatch.setattr(trader, "PAPER_EQUITY_CSV", str(equity_file))
    monkeypatch.setattr(server, "PAPER_EQUITY_CSV", equity_file)
    trader.append_equity_snapshot(10_200, 3_200)
    trader.append_equity_snapshot(float("nan"), 3_000)
    trader.append_equity_snapshot(10_150, 3_150)
    rows = client.get("/api/paper-equity").get_json()
    assert len(rows) == 2
    assert [row["equity"] for row in rows] == [10200, 10150]
    assert [row["cash"] for row in rows] == [3200, 3150]
    assert pd.read_csv(equity_file).shape[0] == 2
