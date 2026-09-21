from types import SimpleNamespace

import pytest

import core.alpaca_trade as broker


class FakeClient:
    def __init__(self):
        self.submitted = None
        self.closed = None

    def get_latest_trade(self, symbol):
        return SimpleNamespace(price=100)

    def submit_order(self, **kwargs):
        self.submitted = kwargs
        return SimpleNamespace(id="paper-order")

    def close_position(self, symbol, **kwargs):
        self.closed = (symbol, kwargs)
        return SimpleNamespace(id="close-order")


def test_submit_order_validates_side(monkeypatch):
    monkeypatch.setattr(broker, "APCA_API_KEY_ID", "paper-key")
    monkeypatch.setattr(broker, "APCA_API_SECRET_KEY", "paper-secret")
    with pytest.raises(ValueError):
        broker.submit_order("AAPL", "invalid", 1)


def test_submit_order_builds_bracket(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(broker, "APCA_API_KEY_ID", "paper-key")
    monkeypatch.setattr(broker, "APCA_API_SECRET_KEY", "paper-secret")
    monkeypatch.setattr(broker, "_client_for", lambda symbol: client)
    broker.submit_order("AAPL", "buy", 2, stop_loss_pct=0.02, take_profit_pct=0.04)
    assert client.submitted["stop_loss"]["stop_price"] == 98.0
    assert client.submitted["take_profit"]["limit_price"] == 104.0


def test_partial_close_passes_quantity(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(broker, "_client_for", lambda symbol: client)
    broker.close_position("AAPL", qty=1.5)
    assert client.closed == ("AAPL", {"qty": 1.5, "percentage": None})


def test_close_rejects_conflicting_amounts():
    with pytest.raises(ValueError):
        broker.close_position("AAPL", qty=1, percentage=50)


@pytest.mark.parametrize("url", [
    "https://api.alpaca.markets", "http://paper-api.alpaca.markets",
    "https://paper-api.alpaca.markets.evil.test", "https://paper-api.alpaca.markets@evil.test",
])
def test_broker_rejects_non_paper_endpoints(monkeypatch, url):
    monkeypatch.setattr(broker, "STOCK_TRADING_URL", url)
    with pytest.raises(RuntimeError, match="paper-trading endpoint"):
        broker._get_client("stocks")


def test_crypto_order_is_gtc_without_bracket(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(broker, "APCA_API_KEY_ID", "paper-key")
    monkeypatch.setattr(broker, "APCA_API_SECRET_KEY", "paper-secret")
    monkeypatch.setattr(broker, "_client_for", lambda symbol: client)
    broker.submit_order("BTCUSD", "buy", 0.001)
    assert client.submitted["time_in_force"] == "gtc"
    assert client.submitted["symbol"] == "BTC/USD"
    assert "order_class" not in client.submitted
    with pytest.raises(ValueError, match="bracket"):
        broker.submit_order("BTCUSD", "buy", 0.001, stop_loss_pct=0.02)
    with pytest.raises(ValueError, match="short"):
        broker.submit_order("BTCUSD", "sell", 0.001)


def test_stock_bracket_rejects_fractional_shares(monkeypatch):
    monkeypatch.setattr(broker, "APCA_API_KEY_ID", "paper-key")
    monkeypatch.setattr(broker, "APCA_API_SECRET_KEY", "paper-secret")
    with pytest.raises(ValueError, match="whole-share"):
        broker.submit_order("AAPL", "buy", 0.5, stop_loss_pct=0.02)
