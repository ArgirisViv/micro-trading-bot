import time
import logging
from datetime import datetime, time as dtime, timezone

from data.live_data_fetch import get_live_data
from core.strategy import apply_strategy
# Lazy imports for trading functions
def get_account():
    from core.alpaca_trade import get_account
    return get_account()

def get_open_orders_count():
    from core.alpaca_trade import get_open_orders_count
    return get_open_orders_count()

def get_open_positions_count():
    from core.alpaca_trade import get_open_positions_count
    return get_open_positions_count()

def get_position(symbol):
    from core.alpaca_trade import get_position
    return get_position(symbol)

def submit_order(symbol, side, qty, **kwargs):
    from core.alpaca_trade import submit_order
    return submit_order(symbol, side, qty, **kwargs)

def close_position(symbol):
    from core.alpaca_trade import close_position
    return close_position(symbol)

def cancel_all_orders():
    from core.alpaca_trade import cancel_all_orders
    return cancel_all_orders()
from core.notifications import send_slack
from config import (
    SYMBOL,
    TIMEFRAME,
    RISK_PER_TRADE,
    MAX_POSITIONS,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
)

# Configure logger with file handler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("paper_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# NYSE market hours in UTC (13:30 - 20:00 UTC = 9:30 AM - 4:00 PM EST)
MARKET_OPEN = dtime(hour=13, minute=30)
MARKET_CLOSE = dtime(hour=20, minute=0)


def _sleep_until_next_bar(tf: str):
    now = datetime.now(timezone.utc)
    if tf.endswith("min"):
        interval = int(tf.replace("min", "")) * 60
    elif tf.endswith("h"):
        interval = int(tf.replace("h", "")) * 3600
    else:
        interval = 60

    secs_today = now.hour * 3600 + now.minute * 60 + now.second
    next_tick = ((secs_today // interval) + 1) * interval
    delta = max(1, next_tick - secs_today)
    logger.info(f"Waiting {delta}s until next {tf} bar…")
    time.sleep(delta)


def run_paper_trading_loop():
    logger.info("🚀 Starting paper-trading loop…")
    prev_sig = 0
    iteration = 0

    try:
        while True:
            iteration += 1
            logger.info(f"=== Iteration {iteration} ===")
            
            # 0) Έλεγχος ωρών αγοράς
            now_t = datetime.now(timezone.utc).time()
            logger.info(f"Current UTC time: {now_t}")
            logger.info(f"Market hours: {MARKET_OPEN} - {MARKET_CLOSE}")
            
            if now_t < MARKET_OPEN or now_t > MARKET_CLOSE:
                logger.info("Market closed or pre-market; sleeping 30m…")
                time.sleep(30 * 60)
                continue

            # 1) Φόρτιση intraday δεδομένων
            logger.info(f"Fetching live data for {SYMBOL}...")
            df = get_live_data(SYMBOL)
            
            if df is None:
                logger.error("get_live_data returned None")
                time.sleep(30)
                continue
                
            if df.empty:
                logger.warning(f"No live data fetched for {SYMBOL}; df shape: {df.shape}")
                logger.warning("Retrying in 30s…")
                time.sleep(30)
                continue
            
            logger.info(f"✅ Data fetched successfully: {df.shape[0]} rows, columns: {list(df.columns)}")
            logger.info(f"Latest data: {df.tail(1)[['close', 'volume']].to_dict('records')}")

            # 2) Εφαρμογή στρατηγικής
            logger.info("Applying strategy...")
            try:
                sig = apply_strategy(df)
                last_sig = sig["signal"].iloc[-1]
                logger.info(f"✅ Strategy applied. Last signal: {last_sig}")
            except Exception as e:
                logger.error(f"❌ Strategy application failed: {e}")
                time.sleep(30)
                continue

            # 3) Έλεγχος εντολών & θέσεων
            logger.info("Checking orders and positions...")
            try:
                open_orders = get_open_orders_count()
                open_count = get_open_positions_count()
                pos = get_position(SYMBOL)
                logger.info(
                    f"✅ Status - Pending orders: {open_orders}, "
                    f"Open positions: {open_count}, "
                    f"qty: {pos.qty if pos else 0}"
                )
            except Exception as e:
                logger.error(f"❌ Failed to get account status: {e}")
                time.sleep(30)
                continue

            # 3a) Cancel pending orders
            if open_orders > 0:
                logger.info(f"Cancelling {open_orders} pending order(s)…")
                try:
                    cancel_all_orders()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Failed to cancel orders: {e}")

            # 4) Exit logic
            if pos:
                if last_sig == 0:
                    logger.info(f"No signal → closing position for {SYMBOL}…")
                    try:
                        close_position(SYMBOL)
                        send_slack(f":stop_sign: Closed position for {SYMBOL} (signal→0)")
                    except Exception as e:
                        logger.error(f"❌ Failed to close position: {e}")
                elif (pos.side == "long" and last_sig == -1) or (
                    pos.side == "short" and last_sig == 1
                ):
                    logger.info(f"Signal reverse → closing position for {SYMBOL}…")
                    try:
                        close_position(SYMBOL)
                        send_slack(f":arrows_counterclockwise: Reversed position for {SYMBOL}")
                    except Exception as e:
                        logger.error(f"❌ Failed to close position: {e}")

            # 5) Entry logic
            if (
                last_sig != 0
                and last_sig != prev_sig
                and open_orders == 0
                and open_count < MAX_POSITIONS
            ):
                side = "buy" if last_sig == 1 else "sell"
                logger.info(f"🎯 Entry signal: {side.upper()} {SYMBOL}")
                
                try:
                    acct = get_account()
                    cash = float(acct.cash)
                    price = df["close"].iloc[-1]
                    raw_qty = (cash * RISK_PER_TRADE) / price
                    qty = max(1, int(raw_qty))

                    order = submit_order(
                        symbol=SYMBOL,
                        side=side,
                        qty=qty,
                        stop_loss_pct=STOP_LOSS_PCT,
                        take_profit_pct=TAKE_PROFIT_PCT,
                    )
                    logger.info(f"✅ Submitted {side} {qty}@{price:.2f}, id={order.id}")
                    send_slack(
                        f":rocket: {side.upper()} {qty} {SYMBOL} @ {price:.2f} (order {order.id})"
                    )

                    prev_sig = last_sig
                except Exception as e:
                    logger.error(f"❌ Failed to submit order: {e}")

            # 6) Sleep until next bar
            logger.info("Sleeping until next bar...")
            _sleep_until_next_bar(TIMEFRAME)

    except Exception as e:
        logger.exception("🔴 Bot crashed with error")
        try:
            send_slack(f":boom: Bot crashed: `{e}`")
        except:
            logger.error("Failed to send Slack notification")
        raise


if __name__ == "__main__":
    run_paper_trading_loop()
