# config.py (env loading)

import os, json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# --- Safe loader: auto-detect UTF-8 / UTF-8-BOM / UTF-16 και ποτέ μην κρασάρεις ---
def _load_env_any(path: Path, override: bool = False):
    if not path.exists():
        return
    try:
        sig = path.read_bytes()[:4]
        if sig.startswith((b"\xff\xfe", b"\xfe\xff")):
            enc = "utf-16"
        elif sig.startswith(b"\xef\xbb\xbf"):
            enc = "utf-8-sig"  # UTF-8 with BOM
        else:
            enc = "utf-8"
        load_dotenv(path, override=override, encoding=enc)
    except Exception as e:
        print(f"⚠️ Skipping {path.name}: {e}")

# 1) Δώσε προτεραιότητα στο .env.local (UTF-8), να υπερισχύει τοπικά
_load_env_any(ROOT / ".env.local", override=True)
# 2) Και μετά φόρτωσε και το .env (αν υπάρχει), χωρίς override
_load_env_any(ROOT / ".env", override=False)

# ---------------------------------------------------------------------
# Βέλτιστες παράμετροι (αν υπάρχουν)
# ---------------------------------------------------------------------
try:
    with open(ROOT / "best_params.json", "r", encoding="utf-8") as f:
        best = json.load(f)
except FileNotFoundError:
    best = {"SMA_FAST": 10, "SMA_SLOW": 30, "RSI_PERIOD": 14, "ATR_PERIOD": 14}

# ---------------------------------------------------------------------
# Helpers για env parsing
# ---------------------------------------------------------------------
def env_list(name: str, sep: str = ","):
    return [x.strip() for x in os.getenv(name, "").split(sep) if x.strip()]

def env_bool(name: str, default: bool = False):
    v = os.getenv(name, str(default))
    return str(v).strip().lower() in {"1", "true", "yes", "on"}

def env_float(name: str, default: float):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return float(default)

def env_int(name: str, default: int):
    try:
        return int(os.getenv(name, default))
    except Exception:
        return int(default)

# ---------------------------------------------------------------------
# API Keys (μόνο από env)
# ---------------------------------------------------------------------
ALPHA_VANTAGE_KEY   = os.getenv("ALPHA_VANTAGE_KEY", "").strip()
APCA_API_KEY_ID     = os.getenv("APCA_API_KEY_ID", "").strip()
APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY", "").strip()

# ---------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------
STOCK_TRADING_URL  = os.getenv("STOCK_TRADING_URL",  "https://paper-api.alpaca.markets")
CRYPTO_TRADING_URL = os.getenv("CRYPTO_TRADING_URL", "https://paper-api.alpaca.markets")
STOCK_BASE_URL     = os.getenv("STOCK_BASE_URL",     "https://data.alpaca.markets/v2")
CRYPTO_BASE_URL    = os.getenv("CRYPTO_BASE_URL",    "https://data.alpaca.markets/v2/crypto")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "").strip()

# ---------------------------------------------------------------------
# Watchlists / Universe prefs
# ---------------------------------------------------------------------
STOCK_WATCHLIST  = env_list("STOCK_WATCHLIST")  or ["AAPL", "MSFT", "GOOG", "TSLA", "AMZN"]
CRYPTO_WATCHLIST = env_list("CRYPTO_WATCHLIST") or ["BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD"]
ASSET_CLASSES    = env_list("ASSET_CLASSES")    or ["stocks", "crypto"]  # π.χ. ["stocks"] ή ["crypto"]

# ---------------------------------------------------------------------
# Trading params (single-symbol loop defaults)
# ---------------------------------------------------------------------
SYMBOL    = os.getenv("SYMBOL", "AAPL")
TIMEFRAME = os.getenv("TIMEFRAME", "5min")
LOOKBACK  = env_int("LOOKBACK", 3)  # ημέρες history για live_data_fetch

# ---------------------------------------------------------------------
# Risk management
# ---------------------------------------------------------------------
RISK_PER_TRADE   = env_float("RISK_PER_TRADE", 0.01)  # 1% equity ανά trade
STOP_LOSS_PCT    = env_float("STOP_LOSS_PCT", 0.02)   # 2%
TAKE_PROFIT_PCT  = env_float("TAKE_PROFIT_PCT", 0.04) # 4%

# Back-compat aliases (αν κάπου παλιότερα χρησιμοποιούνται)
STOP_PCT = STOP_LOSS_PCT
TAKE_PCT = TAKE_PROFIT_PCT

# Trailing / Partial close
TRAILING_STOP_PCT   = env_float("TRAILING_STOP_PCT", 0.01)  # 1% από το υψηλό θέσης
PARTIAL_CLOSE_PCT   = env_float("PARTIAL_CLOSE_PCT", 0.02)  # στο +2%
PARTIAL_CLOSE_RATIO = env_float("PARTIAL_CLOSE_RATIO", 0.5) # 50%

# Position limits
MAX_POSITIONS            = env_int("MAX_POSITIONS", 2)             # single-symbol loop
MAX_POSITIONS_PER_SYMBOL = env_int("MAX_POSITIONS_PER_SYMBOL", 1)  # multi-asset
MAX_PORTFOLIO_POSITIONS  = env_int("MAX_PORTFOLIO_POSITIONS", 4)   # multi-asset συνολικά

# ---------------------------------------------------------------------
# Backtesting params
# ---------------------------------------------------------------------
HISTORICAL_TIMEFRAME = os.getenv("HISTORICAL_TIMEFRAME", "1Day")
HISTORICAL_LOOKBACK  = env_int("HISTORICAL_LOOKBACK", 365)

# ---------------------------------------------------------------------
# Τεχνικοί δείκτες (backtest & strategy)
# ---------------------------------------------------------------------
SMA_FAST   = int(os.getenv("SMA_FAST", best.get("SMA_FAST", 10)))
SMA_SLOW   = int(os.getenv("SMA_SLOW", best.get("SMA_SLOW", 30)))
RSI_PERIOD = int(os.getenv("RSI_PERIOD", best.get("RSI_PERIOD", 14)))

# Για το ATR sizing στα loops (κρατάμε ATR_PERIOD για back-compat)
ATR_PERIOD = int(os.getenv("ATR_PERIOD", best.get("ATR_PERIOD", 14)))
ATR_LEN    = int(os.getenv("ATR_LEN", ATR_PERIOD))
ATR_MULT   = env_float("ATR_MULT", 2.0)

# ---------------------------------------------------------------------
# Runtime options για τα loops (multi-asset ειδικά)
# ---------------------------------------------------------------------
EQUITY_MARKET_HOURS_ONLY = env_bool("EQUITY_MARKET_HOURS_ONLY", True)

# Daily loss / drawdown limits
MAX_DAILY_DRAWDOWN_PCT = env_float("MAX_DAILY_DRAWDOWN_PCT", 0.02)  # 2%
# alias για το loop που διαβάζει env DAILY_MAX_LOSS_PCT
os.environ.setdefault("DAILY_MAX_LOSS_PCT", str(MAX_DAILY_DRAWDOWN_PCT))

# Heartbeat / state / logs
HEARTBEAT_MINUTES = env_int("HEARTBEAT_MINUTES", 15)
STATE_FILE        = os.getenv("STATE_FILE", "state.json")
LOOP_LOG_FILE     = os.getenv("LOOP_LOG_FILE", "multi_asset_loop.log")

MAX_DAILY_ORDERS    = env_int("MAX_DAILY_ORDERS", 100)
ERROR_BACKOFF_START = env_int("ERROR_BACKOFF_START", 5)
ERROR_BACKOFF_MAX   = env_int("ERROR_BACKOFF_MAX", 300)

# ---------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------
USE_MOCK_DATA = env_bool("USE_MOCK_DATA", False)

# ---------------------------------------------------------------------
# Alerts / Integrations (μόνο από env)
# ---------------------------------------------------------------------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
ALERT_EMAILS     = env_list("ALERT_EMAILS")

TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER  = os.getenv("TWILIO_FROM_NUMBER", "").strip()
ALERT_PHONE_NUMBERS = env_list("ALERT_PHONE_NUMBERS")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "").strip()
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ---------------------------------------------------------------------
# VALUE FILTER (Buffett-style overlay για μετοχές)
# ---------------------------------------------------------------------
VALUE_FILTER = env_bool("VALUE_FILTER", True)
VALUE_TOP_N = env_int("VALUE_TOP_N", 150)
VALUE_MIN_MARKET_CAP = env_int("VALUE_MIN_MARKET_CAP", 2_000_000_000)
VALUE_REFRESH_DAYS = env_int("VALUE_REFRESH_DAYS", 7)

VALUE_WEIGHTS = {
    "pe": -1.0,             # μικρότερο καλύτερο
    "pb": -0.6,             # μικρότερο καλύτερο
    "roe": +1.0,            # μεγαλύτερο καλύτερο
    "fcf_yield": +1.0,      # μεγαλύτερο καλύτερο
    "debt_to_equity": -0.7, # μικρότερο καλύτερο
    "profit_margin": +0.6,  # μεγαλύτερο καλύτερο
}
