import pytest
from werkzeug.security import generate_password_hash

from webapp import server


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def forbidden(*args,**kwargs):
        raise AssertionError('Offline test attempted network access')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", generate_password_hash("correct-horse-paper-123", method="pbkdf2:sha256:1000"))
    monkeypatch.setenv("DASHBOARD_ACCOUNTS_DB", str(tmp_path / "dashboard-users.sqlite3"))
    monkeypatch.setenv("CONTROL_FILE", str(tmp_path / "control.json"))
    server.app.secret_key = "test-secret-key-with-at-least-32-characters"
    monkeypatch.setattr(server, "BACKTEST_CSV", tmp_path / "backtest.csv")
    monkeypatch.setattr(server, "WALKFORWARD_CSV", tmp_path / "walkforward.csv")
    monkeypatch.setattr(server, "TRADE_LOG_CSV", tmp_path / "trades.csv")
    monkeypatch.setattr(server, "PAPER_EQUITY_CSV", tmp_path / "paper-equity.csv")
    monkeypatch.setattr(server, "STATE_JSON", tmp_path / "state.json")
    server.app.config.update(TESTING=True)
    client = server.app.test_client()
    response = client.post("/api/auth/login", json={"password": "correct-horse-paper-123"},
                           headers={"X-Requested-With": "Orbit"})
    assert response.status_code == 200
    return client
