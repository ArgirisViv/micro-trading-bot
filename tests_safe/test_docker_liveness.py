import json
from datetime import datetime, timedelta, timezone

from scripts.check_trader_health import heartbeat_is_fresh
from scripts.check_docker_config import check_config


def test_trader_health_checks_loop_heartbeat(tmp_path):
    state = tmp_path / "state.json"
    assert heartbeat_is_fresh(state) is False
    state.write_text(json.dumps({"last_heartbeat": datetime.now(timezone.utc).isoformat()}))
    assert heartbeat_is_fresh(state) is True
    state.write_text(json.dumps({"last_heartbeat": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()}))
    assert heartbeat_is_fresh(state) is False
    state.write_text("not json")
    assert heartbeat_is_fresh(state) is False


def test_compose_preflight_requires_paper_and_auth_without_echoing_secrets(tmp_path):
    env = tmp_path / ".env.local"
    assert check_config(env)
    env.write_text("""DASHBOARD_PASSWORD_HASH=scrypt:hash
DASHBOARD_SESSION_SECRET=0123456789abcdefghijklmnopqrstuvwxyz
APCA_API_KEY_ID=private-key
APCA_API_SECRET_KEY=private-secret
STOCK_TRADING_URL=https://paper-api.alpaca.markets
CRYPTO_TRADING_URL=https://paper-api.alpaca.markets
ASSET_CLASSES=stocks
POLYGON_API_KEY=provider-key
""", encoding="utf-8")
    assert check_config(env) == []
    env.write_text(env.read_text().replace("https://paper-api.alpaca.markets", "https://api.alpaca.markets", 1))
    errors = check_config(env)
    assert any("STOCK_TRADING_URL" in error for error in errors)
    assert "private-secret" not in str(errors)
