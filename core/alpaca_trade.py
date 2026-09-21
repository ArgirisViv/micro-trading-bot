# core/alpaca_trade.py

from __future__ import annotations

import math
import os
import requests
from datetime import datetime, timezone
from urllib.parse import urlsplit

try:
    from alpaca_trade_api.rest import REST, APIError
except ImportError:  # Dashboard and offline tests do not require the broker SDK.
    REST = None
    APIError = None
from config import (
    APCA_API_KEY_ID,
    APCA_API_SECRET_KEY,
    STOCK_TRADING_URL,
    CRYPTO_TRADING_URL,
    STOCK_WATCHLIST,
    CRYPTO_WATCHLIST,
)

# Clients are created lazily so imports, tests and dashboards can start without
# credentials. Credentials are required only when a broker operation is used.
_stock_client = None
_crypto_client = None


class BrokerSession(requests.Session):
    """Bounded broker reads/mutations; requests adapters do not retry POSTs."""
    def request(self,method,url,**kwargs):
        kwargs['timeout']=(5,20)
        kwargs['allow_redirects']=False
        return super().request(method,url,**kwargs)


def _configure_transport(client):
    # Isolated compatibility point for alpaca-trade-api 3.x. Its REST class
    # otherwise retries 429/504 on POST and requests without a timeout.
    client._retry=0
    client._session.close()
    client._session=BrokerSession()
    return client


def _require_paper_endpoint(url: str) -> None:
    """Fail closed if configuration points at a live or disguised broker host."""
    parsed = urlsplit(url)
    if (parsed.scheme, parsed.hostname, parsed.port, parsed.username, parsed.password, parsed.path.rstrip("/"), parsed.query, parsed.fragment) != (
        "https", "paper-api.alpaca.markets", None, None, None, "", "", ""
    ):
        raise RuntimeError("Only the official Alpaca paper-trading endpoint is supported")


def _get_client(asset_class: str) -> REST:
    global _stock_client, _crypto_client
    if asset_class not in {"stocks", "crypto"}:
        raise ValueError("Unsupported asset class")
    # Validate both endpoints on every broker operation, including with cached clients.
    _require_paper_endpoint(STOCK_TRADING_URL)
    _require_paper_endpoint(CRYPTO_TRADING_URL)
    if REST is None:
        raise RuntimeError("alpaca-trade-api is not installed")
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise RuntimeError("Alpaca paper-trading credentials are not configured")
    os.environ['APCA_RETRY_MAX']='0'
    if asset_class == "crypto":
        if _crypto_client is None:
            _crypto_client = _configure_transport(REST(
                APCA_API_KEY_ID, APCA_API_SECRET_KEY,
                base_url=CRYPTO_TRADING_URL, api_version="v2",
            ))
        return _crypto_client
    if _stock_client is None:
        _stock_client = _configure_transport(REST(
            APCA_API_KEY_ID, APCA_API_SECRET_KEY,
            base_url=STOCK_TRADING_URL, api_version="v2",
        ))
    return _stock_client

def _client_for(symbol: str) -> REST:
    """
    Επέστρεψε τον stock client αν το symbol είναι σε STOCK_WATCHLIST,
    αλλιώς τον crypto client (αν υπάρχει στο CRYPTO_WATCHLIST).
    """
    if symbol in STOCK_WATCHLIST:
        return _get_client("stocks")
    if symbol in CRYPTO_WATCHLIST:
        return _get_client("crypto")
    raise ValueError("Symbol is not in a configured watchlist")


def _broker_symbol(symbol: str) -> str:
    """Map provider-style crypto pairs to Alpaca's slash-separated symbol."""
    if symbol in CRYPTO_WATCHLIST and "/" not in symbol and symbol.endswith("USD"):
        return f"{symbol[:-3]}/USD"
    return symbol

def get_account():
    """
    Επιστρέφει το κοινό paper account object (το ίδιο για stocks & crypto).
    """
    return _get_client("stocks").get_account()


def is_stock_market_open() -> bool:
    """Use the broker clock to account for weekends, holidays and US DST."""
    return bool(_get_client("stocks").get_clock().is_open)

def get_all_symbols(asset_class: str) -> list[str]:
    """
    Επιστρέφει όλα τα tradable symbols της κατηγορίας:
      - "stocks" → us_equity
      - "crypto" → crypto
    """
    # διάλεξε client και asset_class για το API
    if asset_class.lower() == "stocks":
        client = _get_client("stocks")
        ac = "us_equity"
    elif asset_class.lower() == "crypto":
        client = _get_client("crypto")
        ac = "crypto"
    else:
        return []

    # φέρε όλα τα active assets αυτού του τύπου
    assets = client.list_assets(status="active", asset_class=ac)
    # κράτησε μόνο τα tradable
    return [a.symbol for a in assets if getattr(a, "tradable", False)]


def get_open_orders_count() -> int:
    """
    Μετράει τα pending orders σε stock & crypto paper λογαριασμό.
    """
    return len(_get_client("stocks").list_orders(status="open", limit=500))


def get_latest_stock_price(symbol: str) -> float:
    """Fresh broker trade used as a common sizing/bracket reference (not fill)."""
    if symbol not in STOCK_WATCHLIST:
        raise ValueError('Stock symbol is not configured')
    trade = _client_for(symbol).get_latest_trade(symbol)
    price = float(trade.price)
    timestamp = trade.timestamp
    if timestamp.tzinfo is None:
        raise ValueError('Broker timestamp is not timezone-aware')
    age = (datetime.now(timezone.utc) - timestamp).total_seconds()
    if not math.isfinite(price) or price <= 0 or not 0 <= age <= 60:
        raise ValueError('Broker reference trade is invalid or stale')
    return price

def get_open_positions_count() -> int:
    """
    Μετράει τις ανοιχτές θέσεις (stocks + crypto).
    """
    return len(_get_client("stocks").list_positions())


def get_positions():
    """Full account snapshot; also includes symbols outside the bot watchlists."""
    return _get_client('stocks').list_positions()


def get_order(order_id: str):
    """GET a known order including bracket legs; errors propagate to fail-closed."""
    if not isinstance(order_id,str) or not order_id:
        raise ValueError('Broker order ID required')
    return _get_client('stocks').get_order(order_id,nested=True)


def get_order_by_client_order_id(client_order_id: str):
    """Only an explicit broker 404 means not found, never an arbitrary exception."""
    if not isinstance(client_order_id,str) or not client_order_id:
        raise ValueError('Client order ID required')
    try:
        return _get_client('stocks').get_order_by_client_order_id(client_order_id)
    except Exception as exc:
        if APIError is not None and isinstance(exc,APIError) and getattr(exc,'status_code',None) == 404:
            return None
        raise


def get_crypto_quote(symbol):
    if symbol not in CRYPTO_WATCHLIST:raise ValueError('Crypto symbol not configured')
    pair=_broker_symbol(symbol)
    quote=_client_for(symbol).get_latest_crypto_quotes([pair])[pair]
    return dict(bid=str(quote.bid_price),ask=str(quote.ask_price),timestamp=quote.timestamp)


def submit_crypto_exit(symbol,qty,client_order_id):
    """Long-only close, stable ID, quantity rechecked immediately before POST."""
    if symbol not in CRYPTO_WATCHLIST:raise ValueError('Crypto symbol not configured')
    if not math.isfinite(float(qty)) or float(qty)<=0:raise ValueError('Invalid close quantity')
    if not isinstance(client_order_id,str) or not 1<=len(client_order_id)<=48:raise ValueError('Invalid exit ID')
    position=get_position(symbol)
    if position is None:raise ValueError('No broker long position')
    broker_qty=float(position.qty)
    if not math.isfinite(broker_qty) or broker_qty<=0 or broker_qty<float(qty):
        raise ValueError('Exit exceeds broker long position')
    client=_client_for(symbol)
    orders=client.list_orders(status='open',limit=500)
    if len(orders)>=500:raise RuntimeError('Open order snapshot may be truncated')
    if any(str(order.symbol).replace('/','')==symbol.replace('/','') for order in orders):
        raise RuntimeError('Conflicting symbol order; exit blocked')
    return client.submit_order(symbol=_broker_symbol(symbol),qty=str(qty),side='sell',
        type='market',time_in_force='gtc',client_order_id=client_order_id)

def get_position(symbol: str):
    """
    Επιστρέφει την ανοιχτή θέση για ένα symbol, ή None αν δεν υπάρχει.
    """
    client = _client_for(symbol)
    try:
        return client.get_position(_broker_symbol(symbol))
    except Exception as exc:
        if APIError is not None and isinstance(exc, APIError) and getattr(exc, "status_code", None) == 404:
            return None
        raise

def submit_order(
    symbol: str,
    side: str,
    qty: float,
    time_in_force: str = "day",
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    reference_price: float | None = None,
    client_order_id: str | None = None,
):
    """
    Υποβάλλει market ή bracket order με stop-loss & take-profit.
    stop_loss_pct, take_profit_pct σε δεκαδική μορφή (π.χ. 0.02 για 2%).
    """
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise RuntimeError("Alpaca paper-trading credentials are not configured")
    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    if not math.isfinite(float(qty)) or qty <= 0:
        raise ValueError("qty must be greater than zero")
    asset_class = "crypto" if symbol in CRYPTO_WATCHLIST else "stocks"
    if asset_class == "crypto":
        if side != "buy":
            raise ValueError("New crypto short positions are not supported")
        if time_in_force not in {"day", "gtc"}:
            raise ValueError("Crypto orders require gtc time in force")
        time_in_force = "gtc"
        if stop_loss_pct is not None or take_profit_pct is not None:
            raise ValueError("Crypto bracket orders are not supported")
    elif symbol not in STOCK_WATCHLIST:
        raise ValueError("Symbol is not in a configured watchlist")
    elif (stop_loss_pct is not None or take_profit_pct is not None) and float(qty) != int(qty):
        raise ValueError("Stock bracket orders require whole-share quantity")
    if asset_class == "stocks" and ((stop_loss_pct is None) != (take_profit_pct is None)):
        raise ValueError("Stock bracket orders require both stop loss and take profit")
    for name, value in (("stop_loss_pct", stop_loss_pct), ("take_profit_pct", take_profit_pct)):
        if value is not None and (not math.isfinite(float(value)) or not 0 < value < 1):
            raise ValueError(f"{name} must be between zero and one")
    client = _client_for(symbol)

    # Crypto market orders do not need a broker quote; the stock quote is used
    # only to build the stock bracket's exit prices.
    price = None
    if stop_loss_pct is not None or take_profit_pct is not None:
        price = float(reference_price) if reference_price is not None else float(
            client.get_latest_trade(_broker_symbol(symbol)).price)
        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid broker quote")

    # 2) Υπολόγισε τιμές SL/TP
    stop_price  = price * (1 - stop_loss_pct)   if (stop_loss_pct  is not None and side=="buy") else \
                  price * (1 + stop_loss_pct)   if (stop_loss_pct  is not None) else None
    limit_price = price * (1 + take_profit_pct) if (take_profit_pct is not None and side=="buy") else \
                  price * (1 - take_profit_pct) if (take_profit_pct is not None) else None

    # 3) Στήσιμο βασικών παραμέτρων
    params = {
        "symbol": _broker_symbol(symbol),
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": time_in_force,
    }
    if client_order_id is not None:
        if not isinstance(client_order_id, str) or not 1 <= len(client_order_id) <= 48:
            raise ValueError('Invalid client order identifier')
        params['client_order_id'] = client_order_id

    # 4) Αν υπάρχουν SL/TP, βάλε bracket order
    if stop_price is not None or limit_price is not None:
        params["order_class"] = "bracket"
        if stop_price is not None:
            params["stop_loss"] = {"stop_price": round(stop_price, 2)}
        if limit_price is not None:
            params["take_profit"] = {"limit_price": round(limit_price, 2)}

    return client.submit_order(**params)

def close_position(symbol: str, qty: float | None = None, percentage: float | None = None):
    """
    Κλείνει τη θέση για το συγκεκριμένο symbol.
    """
    if qty is not None and percentage is not None:
        raise ValueError("Provide either qty or percentage, not both")
    client = _client_for(symbol)
    return client.close_position(_broker_symbol(symbol), qty=qty, percentage=percentage)

def cancel_all_orders():
    """
    Ακύρωσε όλες τις pending εντολές (stocks + crypto).
    """
    return _get_client("stocks").cancel_all_orders()
