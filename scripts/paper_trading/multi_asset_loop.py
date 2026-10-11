# scripts/paper_trading/multi_asset_loop.py

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import csv
import math
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, time as dtime, timezone, timedelta
from typing import Dict, Any, Optional
from runtime_control import read_control
from core.execution_safety import risk_quantity, reset_daily_state, exclusive_runtime
from data.bar_validation import validated_bars, bar_interval
from core.execution_runtime import initialize_ledger, refresh_execution, apply_execution_state

import pandas as pd

from core.notifications import notify
from data.live_data_fetch import get_live_data
from core.enhanced_strategy import apply_enhanced_strategy
from core.alpaca_trade import (
    get_open_orders_count, get_open_positions_count,
    get_position, get_account, submit_order, close_position, cancel_all_orders,
    is_stock_market_open,
    get_latest_stock_price,
)
from core.fundamentals import build_value_universe
from config import (
    ASSET_CLASSES, TIMEFRAME, LOOKBACK, RISK_PER_TRADE,
    MAX_POSITIONS_PER_SYMBOL,      # reserved
    MAX_PORTFOLIO_POSITIONS,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, TRAILING_STOP_PCT,
    PARTIAL_CLOSE_PCT, PARTIAL_CLOSE_RATIO,   # reserved
    # Buffett overlay config
    VALUE_FILTER, VALUE_TOP_N, VALUE_MIN_MARKET_CAP, VALUE_REFRESH_DAYS, VALUE_WEIGHTS,
    # Watchlists
    STOCK_WATCHLIST, CRYPTO_WATCHLIST,
)

# --- Προαιρετικές ρυθμίσεις ATR & market hours (με defaults αν λείπουν από config) ---
try:
    from config import ATR_LEN, ATR_MULT, EQUITY_MARKET_HOURS_ONLY
except Exception:
    ATR_LEN = 14
    ATR_MULT = 2.0
    EQUITY_MARKET_HOURS_ONLY = True

# ------------------------
# Runtime options (env)
# ------------------------
HEARTBEAT_MINUTES   = int(os.getenv("HEARTBEAT_MINUTES", "15"))
STATE_FILE          = os.getenv("STATE_FILE", "state.json")
LOG_FILE            = os.getenv("LOOP_LOG_FILE", "multi_asset_loop.log")
TRADE_LOG_FILE      = os.getenv("TRADE_LOG_FILE", "trade_log.csv")
PAPER_EQUITY_CSV    = os.getenv("PAPER_EQUITY_CSV", "paper_equity.csv")

DAILY_MAX_LOSS_PCT  = float(os.getenv("DAILY_MAX_LOSS_PCT", "0.02"))  # 2% ημερήσιο DD
MAX_DAILY_ORDERS    = int(os.getenv("MAX_DAILY_ORDERS", "100"))

ERROR_BACKOFF_START = int(os.getenv("ERROR_BACKOFF_START", "5"))      # sec
ERROR_BACKOFF_MAX   = int(os.getenv("ERROR_BACKOFF_MAX", "300"))      # sec

MARKET_OPEN  = dtime(hour=13, minute=30)  # UTC
MARKET_CLOSE = dtime(hour=20, minute=0)   # UTC

# ------------------------
# Enhanced Logging
# ------------------------
logger = logging.getLogger("multi_asset_loop")
logger.setLevel(logging.INFO)

# Clear existing handlers to avoid duplicates
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")

# Avoid creating files merely by importing this module (for tests/dashboards).
if __name__ == "__main__":
    fh = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(_fmt)
    logger.addHandler(fh)
else:
    logger.addHandler(logging.NullHandler())

# Console handler (without emojis for Windows compatibility)
sh = logging.StreamHandler()
sh.setFormatter(_fmt)
console_logger = logging.getLogger("console_only")
console_logger.setLevel(logging.INFO)
console_logger.addHandler(sh)

# ------------------------
# Helpers
# ------------------------
def utcnow() -> datetime:
    """Get current UTC time - fixed deprecated datetime.utcnow()"""
    return datetime.now(timezone.utc)

def _sleep_until_next_bar(tf: str) -> bool:
    now = utcnow()
    interval = bar_interval(tf).total_seconds()
    delta = max(1, interval - now.timestamp() % interval)
    logger.info(f"Waiting {delta}s until next {tf} bar...")
    while delta > 0:
        if read_control()["stop_requested"]:
            return True
        chunk = min(30, delta)
        time.sleep(chunk)
        delta -= chunk
        state = load_state()
        state['last_heartbeat'] = utcnow().isoformat()
        save_state(state)
    return False

def send_daily_report(state: dict, account_info: Optional[Any] = None) -> None:
    """Send daily trading report via Telegram"""
    try:
        today = utcnow().date().isoformat()
        
        # Basic daily stats
        daily_orders = state.get("daily_order_count", 0)
        trading_halted = state.get("trading_halted_today", False)
        
        # Get account info if available
        if account_info:
            equity = float(getattr(account_info, "equity", 0.0))
            cash = float(getattr(account_info, "cash", 0.0))
            positions = getattr(account_info, "positions", [])
            num_positions = len(positions) if positions else 0
        else:
            equity = cash = num_positions = 0
        
        # Create daily report message
        report = f"""📊 DAILY REPORT - {today}

🔄 Trading Activity:
• Orders Today: {daily_orders}
• Open Positions: {num_positions}
• Trading Status: {'🟢 Active' if not trading_halted else '🔴 Halted'}

💰 Account Status:
• Total Equity: ${equity:,.2f}
• Available Cash: ${cash:,.2f}

📈 Performance Summary:
• Daily Orders: {daily_orders}
• Market Status: {'🟢 Open' if daily_orders > 0 else '🔴 No Activity'}

---
🤖 Bot Status: Running
⏰ Report Time: {utcnow().strftime('%H:%M:%S')} UTC"""
        
        # Send report
        notify(report)
        logger.info("Daily report sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")
        notify(f"❌ Daily report failed: {e}")

def should_send_daily_report(state: dict) -> bool:
    """Check if it's time to send daily report"""
    try:
        now = utcnow()
        current_time = now.time()
        
        # Send report at 20:30 UTC (after market close)
        report_time = dtime(hour=20, minute=30)
        
        # Check if we haven't sent report today
        last_report_date = state.get("last_daily_report_date", "")
        today = now.date().isoformat()
        
        return (current_time >= report_time and 
                last_report_date != today)
                
    except Exception as e:
        logger.error(f"Error checking daily report timing: {e}")
        return False

def should_send_weekly_report(state: dict) -> bool:
    """Check if it's time to send weekly report (every Sunday at 21:00 UTC)"""
    try:
        now = utcnow()
        current_time = now.time()
        
        # Send weekly report every Sunday at 21:00 UTC
        weekly_report_time = dtime(hour=21, minute=0)
        
        # Check if it's Sunday and we haven't sent report this week
        is_sunday = now.weekday() == 6  # Sunday = 6
        last_weekly_report_date = state.get("last_weekly_report_date", "")
        today = now.date().isoformat()
        
        return (is_sunday and 
                current_time >= weekly_report_time and 
                last_weekly_report_date != today)
                
    except Exception as e:
        logger.error(f"Error checking weekly report timing: {e}")
        return False

def send_weekly_report(state: dict, account_info: Optional[Any] = None) -> None:
    """Send weekly trading report via Telegram"""
    try:
        today = utcnow().date().isoformat()
        
        # Weekly stats
        weekly_orders = state.get("weekly_order_count", 0)
        trading_days = state.get("trading_days_this_week", 0)
        
        # Get account info if available
        if account_info:
            equity = float(getattr(account_info, "equity", 0.0))
            cash = float(getattr(account_info, "cash", 0.0))
            positions = getattr(account_info, "positions", [])
            num_positions = len(positions) if positions else 0
        else:
            equity = cash = num_positions = 0
        
        # Create weekly report message
        report = f"""📈 WEEKLY REPORT - Week ending {today}

🔄 Weekly Activity:
• Total Orders: {weekly_orders}
• Trading Days: {trading_days}
• Open Positions: {num_positions}

💰 Account Status:
• Total Equity: ${equity:,.2f}
• Available Cash: ${cash:,.2f}

📊 Weekly Summary:
• Average Daily Orders: {weekly_orders/max(trading_days, 1):.1f}
• Trading Activity: {'🟢 Active' if weekly_orders > 0 else '🔴 Low Activity'}

---
🤖 Bot Status: Running
⏰ Report Time: {utcnow().strftime('%H:%M:%S')} UTC
📅 Week: {utcnow().strftime('%Y-%m-%d')}"""
        
        # Send report
        notify(report)
        logger.info("Weekly report sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}")
        notify(f"❌ Weekly report failed: {e}")

def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            if not isinstance(state, dict):
                raise ValueError('Runtime state must be an object')
            return state
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise RuntimeError('Runtime state is unreadable; refusing automatic recovery') from exc

def save_state(state: Dict[str, Any]):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_FILE)


def append_trade_event(
    symbol: str,
    side: str,
    price: float,
    qty: float,
    source: str,
    pnl_pct: Optional[float] = None,
):
    """Record submission only; broker acceptance is not a confirmed fill/P&L."""
    fields = ["timestamp", "event_type", "side", "symbol", "price", "qty", "source", "pnl_pct"]
    try:
        exists = os.path.exists(TRADE_LOG_FILE) and os.path.getsize(TRADE_LOG_FILE) > 0
        with open(TRADE_LOG_FILE, "a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            if not exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": utcnow().isoformat(),
                "event_type": "order_submitted",
                "side": side,
                "symbol": symbol,
                "price": round(float(price), 8),
                "qty": round(float(qty), 8),
                "source": source,
                "pnl_pct": "",
            })
    except (OSError, ValueError) as exc:
        # A reporting failure must never make the loop forget a broker-accepted
        # order and retry it as though nothing happened.
        logger.error("Could not append trade event: %s", exc)


def append_equity_snapshot(equity: float, cash: float) -> None:
    """Persist broker-reported paper equity; this is not a strategy return."""
    if not all(math.isfinite(value) and value >= 0 for value in (equity, cash)):
        return
    try:
        exists = os.path.exists(PAPER_EQUITY_CSV) and os.path.getsize(PAPER_EQUITY_CSV) > 0
        with open(PAPER_EQUITY_CSV, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if not exists:
                writer.writerow(["timestamp", "equity", "cash"])
            writer.writerow([utcnow().isoformat(), round(equity, 2), round(cash, 2)])
    except OSError as exc:
        logger.error("Could not record paper equity: %s", exc)

def safe_call(func, *args, **kwargs):
    """Safe function call with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error('Function %s failed (%s); details suppressed', func.__name__, type(e).__name__)
        return None

def _atr_last(df: pd.DataFrame, length: int) -> Optional[float]:
    """Calculate ATR from DataFrame"""
    try:
        if len(df) < length:
            return None
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=length).mean().iloc[-1]
        return float(atr) if pd.notna(atr) else None
    except Exception as e:
        logger.error(f"ATR calculation failed: {e}")
        return None

def _position_size_from_atr(equity: float, cash: float, price: float, atr_val: Optional[float]) -> float:
    """Compatibility name: sizing uses the actual fixed stop, NOT ATR."""
    try:
        return risk_quantity(equity, cash, price, STOP_LOSS_PCT, RISK_PER_TRADE)
    except Exception as e:
        logger.error(f"Position sizing failed: {e}")
        return 0.0

def ensure_sym_keys(state: Dict[str, Any], symbol: str):
    """Ensure all required keys exist for a symbol"""
    required_keys = [
        "entry_price", "trailing_max", "partial_done", "prev_sig"
    ]
    for key in required_keys:
        if key not in state:
            state[key] = {}
        if symbol not in state[key]:
            if key in ["entry_price", "trailing_max"]:
                state[key][symbol] = None
            elif key == "partial_done":
                state[key][symbol] = False
            elif key == "prev_sig":
                state[key][symbol] = 0

def is_crypto_symbol(symbol: str) -> bool:
    """Check if symbol is crypto (contains '/' or ends with 'USD')"""
    return "/" in symbol or symbol.endswith("USD") or symbol.endswith("USDT")


def entries_enabled() -> bool:
    """A missing or corrupt operator control blocks every new entry."""
    return not read_control()["paused"]

def should_trade_symbol(symbol: str, current_time: dtime) -> bool:
    """Determine if we should trade a symbol based on asset type and current time"""
    if is_crypto_symbol(symbol):
        # Crypto trades 24/7
        logger.debug(f"🪙 {symbol}: Crypto symbol - trading 24/7")
        return True
    else:
        # Stocks follow market hours
        is_market_open = MARKET_OPEN <= current_time <= MARKET_CLOSE
        logger.debug(f"{symbol}: Stock symbol - market {'open' if is_market_open else 'closed'}")
        return is_market_open

def run_multi_asset_loop():
    with exclusive_runtime(STATE_FILE + '.lock'):
        _run_multi_asset_loop()


def _run_multi_asset_loop():
    """Main multi-asset trading loop with enhanced logging and mixed asset support"""
    logger.info("Starting multi-asset trading loop...")
    console_logger.info("Starting multi-asset trading loop...")
    notify("Multi-asset loop started")
    
    # Initialize state
    state = load_state()
    if not state:
        state = {
            "entry_price": {},
            "trailing_max": {},
            "partial_done": {},
            "prev_sig": {},
            "trading_halted_today": False,
            "daily_order_count": 0,
            "last_reset_date": utcnow().date().isoformat(),
            "daily_start_equity": None,
        }
        save_state(state)

    ledger = initialize_ledger(state, STATE_FILE)
    save_state(state)

    # Reset daily counters if new day
    today = utcnow().date().isoformat()
    if state.get("last_reset_date") != today:
        state["trading_halted_today"] = False
        state["daily_order_count"] = 0
        state["last_reset_date"] = today
        state["daily_start_equity"] = None
        logger.info("New trading day - resetting daily counters")
        save_state(state)
    
    no_data_notified = set()
    iteration = 0
    
    try:
        while True:
            if read_control()["stop_requested"]:
                logger.info("Stop requested by dashboard; exiting paper loop without closing positions.")
                break
            iteration += 1
            logger.info(f"=== Multi-Asset Loop Iteration {iteration} ===")
            console_logger.info(f"=== Multi-Asset Loop Iteration {iteration} ===")
            
            # Get current time
            now = utcnow()
            reset_daily_state(state, now)
            current_time = now.time()
            # Persist a real liveness signal for the monitoring dashboard. The
            # UI deliberately reports the bot as offline when this timestamp is
            # stale instead of assuming that a configured bot is running.
            state["last_heartbeat"] = now.isoformat()
            state["entries_paused"] = not entries_enabled()
            save_state(state)
            # Reconcile BEFORE strategy/feed/market-clock gates, including when
            # entries are paused or the stock market is closed. Never POST here.
            execution = refresh_execution(ledger)
            apply_execution_state(state,execution)
            save_state(state)
            
            logger.info(f"Current UTC time: {now.strftime('%H:%M:%S')}")
            console_logger.info(f"Current UTC time: {now.strftime('%H:%M:%S')}")
            logger.info(f"Market hours: {MARKET_OPEN} - {MARKET_CLOSE}")
            console_logger.info(f"Market hours: {MARKET_OPEN} - {MARKET_CLOSE}")
            logger.info(f"Asset classes: {ASSET_CLASSES}")
            console_logger.info(f"Asset classes: {ASSET_CLASSES}")
            
            # SMART ASSET FILTERING - Ultra-efficient approach
            try:
                # Get symbols from watchlists instead of all available symbols
                all_symbols = []
                if "stocks" in ASSET_CLASSES:
                    all_symbols.extend(STOCK_WATCHLIST)
                if "crypto" in ASSET_CLASSES:
                    all_symbols.extend(CRYPTO_WATCHLIST)
                
                if not all_symbols:
                    logger.warning("No symbols available - sleeping 60 seconds...")
                    console_logger.warning("No symbols available - sleeping 60 seconds...")
                    time.sleep(60)
                    continue
                
                # Ultra-fast asset categorization
                crypto_symbols = [s for s in all_symbols if is_crypto_symbol(s)]
                stock_symbols = [s for s in all_symbols if not is_crypto_symbol(s)]
                
                logger.info(f"Asset breakdown - Crypto: {len(crypto_symbols)}, Stocks: {len(stock_symbols)}")
                console_logger.info(f"Asset breakdown - Crypto: {len(crypto_symbols)}, Stocks: {len(stock_symbols)}")
                
                # SMART TRADING DECISION - Process only what we can trade
                symbols_to_process = []
                
                is_market_open = False
                if stock_symbols:
                    broker_clock = safe_call(is_stock_market_open)
                    is_market_open = broker_clock is True
                    if broker_clock is None:
                        logger.warning("Broker clock unavailable; skipping stock entries")
                
                if crypto_symbols and stock_symbols:
                    # Mixed portfolio - crypto trades 24/7, stocks only during market hours
                    if is_market_open:
                        symbols_to_process = crypto_symbols + stock_symbols
                        logger.info("Mixed assets - market open: trading crypto + stocks")
                        console_logger.info("Mixed assets - market open: trading crypto + stocks")
                    else:
                        symbols_to_process = crypto_symbols  # Only crypto when market closed
                        logger.info("Mixed assets - market closed: trading only crypto")
                        console_logger.info("Mixed assets - market closed: trading only crypto")
                elif crypto_symbols and not stock_symbols:
                    # Only crypto - trade 24/7
                    symbols_to_process = crypto_symbols
                    logger.info("Only crypto symbols - trading 24/7")
                    console_logger.info("Only crypto symbols - trading 24/7")
                elif stock_symbols and not crypto_symbols:
                    # Only stocks - follow market hours strictly
                    if is_market_open:
                        symbols_to_process = stock_symbols
                        logger.info("Only stock symbols - market open: trading")
                        console_logger.info("Only stock symbols - market open: trading")
                    else:
                        logger.info("Stock market closed or clock unavailable; checking again in 60 seconds")
                        time.sleep(60)
                        continue
                else:
                    # No symbols - sleep
                    logger.warning("⚠️ No symbols available - sleeping 60 seconds...")
                    console_logger.warning("No symbols available - sleeping 60 seconds...")
                    time.sleep(60)
                    continue
            
                # Skip iteration if no symbols to process
                if not symbols_to_process:
                    logger.info("⏰ No symbols to process this iteration - sleeping 60 seconds...")
                    console_logger.info("No symbols to process this iteration - sleeping 60 seconds...")
                    time.sleep(60)
                    continue
                
                logger.info(f"Processing {len(symbols_to_process)} symbols this iteration")
                console_logger.info(f"Processing {len(symbols_to_process)} symbols this iteration")
                
            except Exception as e:
                logger.error(f"Failed to get symbols for asset analysis: {e}")
                console_logger.error(f"Failed to get symbols for asset analysis: {e}")
                time.sleep(30)
                continue

            # Get account info
            try:
                acct = safe_call(get_account)
                if not acct:
                    logger.error("Failed to get account info - retrying in 30s")
                    time.sleep(30)
                    continue
                
                equity = float(getattr(acct, "equity", 0.0))
                cash_available = float(getattr(acct, "cash", 0.0))
                if not math.isfinite(equity) or not math.isfinite(cash_available) or equity <= 0:
                    raise ValueError('Invalid broker account values')
                stored_start_equity = state.get("daily_start_equity")
                if stored_start_equity is None:
                    state["daily_start_equity"] = equity
                    stored_start_equity = equity
                    save_state(state)
                start_equity = float(stored_start_equity)
                daily_drawdown = ((start_equity - equity) / start_equity) if start_equity > 0 else 0.0
                state["account_equity"] = equity
                state["account_cash"] = cash_available
                append_equity_snapshot(equity, cash_available)
                state["daily_pnl"] = equity - start_equity
                state["daily_pnl_pct"] = ((equity / start_equity) - 1.0) * 100 if start_equity > 0 else 0.0
                if daily_drawdown >= DAILY_MAX_LOSS_PCT:
                    state["trading_halted_today"] = True
                    save_state(state)
                    logger.critical("Daily loss limit reached (%.2f%%); new entries halted", daily_drawdown * 100)
                logger.info(f"Account equity: ${equity:,.2f}")
                console_logger.info(f"Account equity: ${equity:,.2f}")
            except Exception as e:
                logger.error(f"Account info error: {e}")
                console_logger.error(f"Account info error: {e}")
                time.sleep(30)
                continue
            
            # Get current positions and orders
            try:
                total_positions = safe_call(get_open_positions_count)
                open_orders_total = safe_call(get_open_orders_count)
                if total_positions is None or open_orders_total is None:
                    logger.error("Broker position/order status unavailable; skipping iteration")
                    time.sleep(30)
                    continue
                state["broker_positions_count"] = int(total_positions)
                state["open_orders_count"] = int(open_orders_total)
                save_state(state)
                logger.info(f"Current status - Positions: {total_positions}, Pending orders: {open_orders_total}")
                console_logger.info(f"Current status - Positions: {total_positions}, Pending orders: {open_orders_total}")
            except Exception as e:
                logger.error(f"Failed to get positions/orders: {e}")
                console_logger.error(f"Failed to get positions/orders: {e}")
                time.sleep(30)
                continue
            
            # Existing orders may include protective stock bracket legs. Never
            # cancel the entire account's orders from a monitoring loop.
            if open_orders_total > 0:
                logger.info("%d broker orders open; new entries disabled", open_orders_total)

            # ULTRA-EFFICIENT SYMBOL PROCESSING - Only process what we can trade
            for sym in symbols_to_process:
                try:
                    console_logger.info(f"Processing symbol: {sym}")
                    
                    # No need to check should_trade_symbol here - we already filtered above
                    ensure_sym_keys(state, sym)

                    # Fetch data with detailed logging
                    logger.info(f"Fetching data for {sym}...")
                    df = get_live_data(sym)

                    # Enhanced data validation logging
                    if df is None:
                        logger.warning(f"⚠️ {sym}: get_live_data returned None")
                        # Αφαιρούμε το notification - μόνο logging
                        continue
                        
                    if df.empty:
                        logger.warning(f"{sym}: get_live_data returned empty DataFrame (shape: {df.shape})")
                        # Αφαιρούμε το notification - μόνο logging
                        continue
                    try:
                        df = validated_bars(df, TIMEFRAME, now=utcnow())
                    except ValueError as exc:
                        state.setdefault('data_issues', {})[sym] = str(exc)
                        save_state(state)
                        continue
                    state.setdefault('data_issues', {}).pop(sym, None)
                    
                    # Data fetched successfully
                    logger.info(f"{sym}: Data fetched successfully - {df.shape[0]} rows, columns: {list(df.columns)}")
                    logger.info(f"{sym}: Latest data - Close: ${df['close'].iloc[-1]:.2f}, Volume: {df['volume'].iloc[-1]:,}")
                    
                    # Clear no-data notification if data is back
                    if sym in no_data_notified:
                        logger.info(f"{sym}: Data restored - clearing no-data notification")
                        no_data_notified.discard(sym)

                    # Apply enhanced strategy with error handling
                    try:
                        logger.info(f"{sym}: Applying enhanced strategy...")
                        console_logger.info(f"Applying enhanced strategy for {sym}...")
                        sig_df = apply_enhanced_strategy(df, sym)
                        # Handle NaN values in signal
                        signal_val = sig_df["signal"].iloc[-1]
                        last_sig = int(signal_val) if not pd.isna(signal_val) else 0
                        confidence = float(sig_df["confidence_score"].iloc[-1]) if "confidence_score" in sig_df.columns else 0.5
                        risk_level = sig_df["risk_level"].iloc[-1] if "risk_level" in sig_df.columns else "UNKNOWN"
                        
                        logger.info(f"{sym}: Enhanced strategy applied - Signal: {last_sig}, Confidence: {confidence:.2f}, Risk: {risk_level}")
                        console_logger.info(f"{sym}: Enhanced strategy applied - Signal: {last_sig}, Confidence: {confidence:.2f}, Risk: {risk_level}")
                        
                        # Log additional insights if available
                        if "technical_signal" in sig_df.columns:
                            # Handle NaN values in technical signal
                            tech_signal_val = sig_df["technical_signal"].iloc[-1]
                            tech_sig = int(tech_signal_val) if not pd.isna(tech_signal_val) else 0
                            logger.info(f"{sym}: Technical signal: {tech_sig}")
                            console_logger.info(f"{sym}: Technical signal: {tech_sig}")
                        
                        if "ml_prediction" in sig_df.columns:
                            # Handle NaN values in ML prediction
                            ml_signal_val = sig_df["ml_prediction"].iloc[-1]
                            ml_sig = int(ml_signal_val) if not pd.isna(ml_signal_val) else 0
                            ml_conf = float(sig_df["ml_confidence"].iloc[-1]) if "ml_confidence" in sig_df.columns else 0.0
                            logger.info(f"{sym}: ML prediction: {ml_sig}, Confidence: {ml_conf:.2f}")
                            console_logger.info(f"{sym}: ML prediction: {ml_sig}, Confidence: {ml_conf:.2f}")
                        
                        if "fundamental_score" in sig_df.columns:
                            fund_score = float(sig_df["fundamental_score"].iloc[-1])
                            logger.info(f"{sym}: Fundamental score: {fund_score:.2f}")
                            console_logger.info(f"{sym}: Fundamental score: {fund_score:.2f}")
                            
                    except Exception as e:
                        logger.error(f"{sym}: Enhanced strategy application failed: {e}")
                        console_logger.error(f"{sym}: Enhanced strategy application failed: {e}")
                        continue

                    # Get position info
                    try:
                        # Broker errors must never be mistaken for "no position".
                        pos = get_position(sym)
                        has_pos = bool(pos)
                        # Pre-existing/manual positions are never silently adopted.
                        owned = any(row['symbol'] == sym and row['broker_quantity_verified']
                                    for row in state.get('managed_positions', []))
                        if has_pos and not owned:
                            state.setdefault('external_positions', {})[sym] = True
                            save_state(state)
                            continue
                        logger.info(f"{sym}: Position status - Has position: {has_pos}")
                        console_logger.info(f"{sym}: Position status - Has position: {has_pos}")
                        if has_pos and state["entry_price"][sym] is None:
                            broker_entry = float(getattr(pos, "avg_entry_price", 0) or 0)
                            if broker_entry <= 0:
                                logger.warning("%s: Broker position has no valid average fill price", sym)
                                continue
                            state["entry_price"][sym] = broker_entry
                            state["trailing_max"][sym] = max(broker_entry, float(df["close"].iloc[-1]))
                            save_state(state)
                        elif not has_pos and state["entry_price"][sym] is not None:
                            state["entry_price"][sym] = None
                            state["trailing_max"][sym] = None
                            state["partial_done"][sym] = False
                            state['prev_sig'][sym] = 0
                            save_state(state)
                    except Exception as e:
                        logger.error(f"{sym}: Failed to get position: {e}")
                        console_logger.error(f"{sym}: Failed to get position: {e}")
                        continue

                    # Stock exits belong to broker bracket legs. The unsafe
                    # legacy crypto close path has been removed from this runtime;
                    # ledger-backed software exits are a separate stage-3 task.

                    # Entry logic with enhanced logging
                    can_trade = (
                        not state["trading_halted_today"]
                        and entries_enabled()
                        and state["daily_order_count"] < int(MAX_DAILY_ORDERS)
                        and total_positions < int(MAX_PORTFOLIO_POSITIONS)
                        and open_orders_total == 0
                        and not state.get('execution_uncertain', False)
                        and os.getenv('PAPER_ENTRIES_APPROVED', 'false').lower() == 'true'
                        # Software crypto exits need independent quote/reconciliation work.
                        and not is_crypto_symbol(sym)
                        and state.get('entry_bars', {}).get(sym) != df.index[-1].isoformat()
                        and execution['pending_entries'] == 0
                    )

                    if (
                        last_sig == 1  # Long-only entries; a negative signal is never a short sale.
                        and last_sig != state["prev_sig"][sym]
                        and not has_pos
                        and can_trade
                    ):
                        try:
                            price = get_latest_stock_price(sym)
                            atr_val = _atr_last(df, int(ATR_LEN))
                            qty = _position_size_from_atr(equity=equity, cash=cash_available, price=price, atr_val=atr_val)
                            if qty <= 0:
                                logger.warning(f"{sym}: No affordable risk-compliant position size")
                                continue
                            if not entries_enabled():
                                logger.warning("%s: Entry paused before order submission", sym)
                                continue
                            if not is_crypto_symbol(sym):
                                qty = float(int(qty))  # Alpaca stock brackets require whole shares.
                                if qty < 1:
                                    logger.info("%s: Insufficient cash for whole-share stock bracket", sym)
                                    continue
                            side = "buy"

                            logger.info(f"{sym}: Submitting {side} order - Qty: {qty}, Price: ${price:.2f}")
                            console_logger.info(f"{sym}: Submitting {side} order - Qty: {qty}, Price: ${price:.2f}")
                            atr_text = f"{atr_val:.4f}" if atr_val is not None else "N/A"
                            logger.info(f"{sym}: ATR: {atr_text}, Cash: ${cash_available:,.2f}")
                            console_logger.info(f"{sym}: ATR: {atr_text}, Cash: ${cash_available:,.2f}")
                            
                            # Αφαιρούμε το notification - μόνο logging
                            
                            # Persist BEFORE the network mutation. A crash or timeout
                            # leaves a durable lock; never blindly repeat this intent.
                            intent, created = ledger.prepare_entry(sym,qty,price,df.index[-1].isoformat())
                            if not created:
                                logger.warning('%s: Intent already exists; not resubmitting',sym)
                                continue
                            client_order_id = intent['client_id']
                            state['execution_uncertain'] = True
                            state.setdefault('entry_bars', {})[sym] = df.index[-1].isoformat()
                            state['last_order_intent'] = {
                                'client_order_id': client_order_id, 'symbol': sym,
                                'qty': qty, 'reference_price': price,
                                'bar_start': df.index[-1].isoformat(),
                                'created_at': utcnow().isoformat(), 'status': 'unconfirmed',
                            }
                            save_state(state)
                            order = safe_call(
                                submit_order,
                                symbol=sym,
                                side=side,
                                qty=qty,
                                stop_loss_pct=None if is_crypto_symbol(sym) else float(STOP_LOSS_PCT),
                                take_profit_pct=None if is_crypto_symbol(sym) else float(TAKE_PROFIT_PCT),
                                reference_price=price,
                                client_order_id=client_order_id,
                            )
                            if order is None:
                                # Timeout does NOT prove rejection: block all subsequent entries.
                                state['execution_uncertain'] = True
                                ledger.mark_uncertain(client_order_id)
                                save_state(state)
                                logger.error('%s: Unconfirmed submission; new entries locked', sym)
                                continue
                            # Broker ack can include an immediate partial/full fill.
                            # Ownership derives only from this validated snapshot.
                            try:
                                ledger.observe_tree(client_order_id, order)
                            except Exception:
                                state['execution_uncertain'] = True
                                save_state(state)
                                logger.error('%s: Broker acknowledgment requires reconciliation',sym)
                                continue
                            append_trade_event(sym, side, price, qty, "strategy_signal")
                            
                            # Trade notification - ΜΟΝΟ αυτό στέλνουμε!
                            notify(f"Paper order submitted: {side.upper()} {qty} {sym} (signal price ${price:.2f}; fill unconfirmed)")
                            
                            # Update state
                            # No broker fill has been confirmed yet. A later
                            # iteration observes the position before showing it.
                            state["entry_price"][sym] = None
                            state["trailing_max"][sym] = None
                            state["partial_done"][sym] = False
                            state["prev_sig"][sym] = last_sig
                            state["daily_order_count"] += 1
                            total_positions += 1
                            cash_available = max(0.0, cash_available - qty * price)
                            open_orders_total += 1
                            state.setdefault('submitted_symbols', []).append(sym)
                            state['last_order_intent']['status'] = 'submitted'
                            state['last_order_intent']['broker_order_id'] = str(
                                order.get('id','') if isinstance(order,dict) else getattr(order,'id',''))
                            state['execution_uncertain'] = ledger.snapshot()['blocked']
                            save_state(state)
                            
                            logger.info(f"{sym}: Order submitted successfully - State updated")
                            console_logger.info(f"{sym}: Order submitted successfully - State updated")
                            
                        except Exception as e:
                            logger.error(f"{sym}: Entry logic error: {e}")
                            console_logger.error(f"{sym}: Entry logic error: {e}")
                            
                except Exception as e:
                    logger.error(f"{sym}: Symbol processing error: {e}")
                    console_logger.error(f"{sym}: Symbol processing error: {e}")
                    continue

            # Check and send daily report
            if should_send_daily_report(state):
                try:
                    account_info = safe_call(get_account)
                    send_daily_report(state, account_info)
                    state["last_daily_report_date"] = utcnow().date().isoformat()
                    save_state(state)
                    logger.info("Daily report sent and state updated")
                except Exception as e:
                    logger.error(f"Failed to send daily report: {e}")
            
            # Check and send weekly report
            if should_send_weekly_report(state):
                try:
                    account_info = safe_call(get_account)
                    send_weekly_report(state, account_info)
                    state["last_weekly_report_date"] = utcnow().date().isoformat()
                    save_state(state)
                    logger.info("Weekly report sent and state updated")
                except Exception as e:
                    logger.error(f"Failed to send weekly report: {e}")
            
            # Sleep until next bar with logging
            logger.info("Sleeping until next bar...")
            console_logger.info("Sleeping until next bar...")
            if _sleep_until_next_bar(TIMEFRAME):
                logger.info("Stop requested by dashboard; exiting paper loop without closing positions.")
                break

    except Exception as e:
        logger.exception("Multi-asset loop crashed with error")
        # Αφαιρούμε το notification - μόνο logging
        raise


if __name__ == "__main__":
    run_multi_asset_loop()
