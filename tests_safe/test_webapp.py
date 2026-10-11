from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from webapp import server


def test_health_and_security_headers(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_empty_dashboard_is_offline_and_stable(client):
    response = client.get("/api/overview")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runtime"]["status"] == "offline"
    assert payload["activity"]["open_positions"] == 0
    assert payload["backtest"] == {}
    assert payload["walkforward"] == {}


def test_state_filters_closed_positions_and_uses_heartbeat(client, tmp_path):
    server.STATE_JSON.write_text(json.dumps({
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "entry_price": {"AAPL": 192.25, "MSFT": None},
        "trailing_max": {"AAPL": 196.0, "MSFT": None},
        "daily_order_count": 3,
        "account_equity": 25_250.5,
        "account_cash": 10_000,
        "daily_pnl": 250.5,
        "daily_pnl_pct": 1.002,
        "open_orders_count": 1,
    }), encoding="utf-8")

    payload = client.get("/api/state").get_json()

    assert payload["runtime"]["status"] == "paused"
    assert payload["runtime"]["entries_paused"] is True
    assert payload["daily_order_count"] == 3
    assert payload["account_equity"] == 25_250.5
    assert payload["account_cash"] == 10_000
    assert payload["open_orders_count"] == 1
    assert payload["positions"] == [{
        "entry_price": 192.25,
        "symbol": "AAPL",
        "trailing_high": 196.0,
    }]


def test_backtest_metrics_are_computed_from_strategy_returns(client):
    pd.DataFrame({
        "timestamp": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "close": [100, 101, 100],
        "StratReturn": [0.0, 0.10, -0.05],
    }).to_csv(server.BACKTEST_CSV, index=False)

    overview = client.get("/api/overview").get_json()["backtest"]
    rows = client.get("/api/backtest").get_json()

    assert overview["bars"] == 3
    assert overview["total_return_pct"] == pytest.approx(4.5)
    assert overview["max_drawdown_pct"] == pytest.approx(-5.0)
    assert rows[-1]["equity"] == pytest.approx(1.045)
    assert rows[-1]["benchmark"] == pytest.approx(1.0)
    assert rows[-1]["drawdown_pct"] == pytest.approx(-5.0)


def test_trade_level_win_rate_and_monthly_performance(client):
    pd.DataFrame({
        "timestamp": [
            "2026-01-01", "2026-01-02", "2026-01-03",
            "2026-01-04", "2026-02-01", "2026-02-02",
        ],
        "close": [100, 110, 108, 108, 103, 103],
        "Position": [0, 1, 1, 0, 1, 0],
        "StratReturn": [0, 0.10, -0.02, 0, -0.05, 0],
    }).to_csv(server.BACKTEST_CSV, index=False)

    payload = client.get("/api/performance").get_json()
    stats = payload["trades"]

    assert stats["source"] == "backtest-trades"
    assert stats["total_trades"] == 2
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert stats["win_rate_pct"] == pytest.approx(50.0)
    assert stats["profit_factor"] == pytest.approx(1.56)
    assert len(payload["monthly_returns"]) == 2


def test_realized_trade_log_takes_priority_for_win_rate(client):
    pd.DataFrame({
        "timestamp": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "symbol": ["AAPL", "MSFT", "BTCUSD"],
        "pnl": [100, -50, 0],
    }).to_csv(server.TRADE_LOG_CSV, index=False)

    stats = client.get("/api/performance").get_json()["trades"]

    assert stats["source"] == "live-dollar-pnl"
    assert stats["win_rate_pct"] == pytest.approx(100 / 3)
    assert stats["profit_factor"] == pytest.approx(2.0)


def test_partial_close_events_do_not_inflate_trade_win_rate(client):
    pd.DataFrame({
        "event_type": ["entry", "partial_close", "close"],
        "symbol": ["AAPL", "AAPL", "AAPL"],
        "pnl_pct": [None, 0.02, -0.01],
    }).to_csv(server.TRADE_LOG_CSV, index=False)

    stats = client.get("/api/performance").get_json()["trades"]

    assert stats["total_trades"] == 1
    assert stats["wins"] == 0
    assert stats["losses"] == 1


def test_malformed_input_does_not_crash_api(client):
    server.BACKTEST_CSV.write_text("not,the,expected,columns\n1,2,3,4\n", encoding="utf-8")
    server.STATE_JSON.write_text(json.dumps({
        "daily_order_count": "not-a-number",
        "entry_price": {"AAPL": "invalid", "MSFT": -5},
    }), encoding="utf-8")

    assert client.get("/api/backtest").get_json() == []
    state_payload = client.get("/api/state").get_json()
    assert state_payload["runtime"]["status"] == "offline"
    assert state_payload["positions"] == []
    assert state_payload["daily_order_count"] == 0


def test_config_endpoint_does_not_expose_credentials(client):
    payload = client.get("/api/config").get_json()
    serialized = json.dumps(payload).lower()

    assert "api_key" not in serialized
    assert "secret" not in serialized
    assert "token" not in serialized


def test_static_app_and_history_fallback(client):
    root = client.get("/")
    fallback = client.get("/overview/deep-link")

    assert root.status_code == 200
    assert fallback.status_code == 200
    assert b"Aether AI" in root.data
    assert b'AETHER AI TERMINAL' in root.data
