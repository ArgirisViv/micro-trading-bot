"""Local monitoring API and static dashboard for the paper-trading bot."""

from __future__ import annotations

import json
import math
import os
import secrets
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from runtime_control import read_control, request_stop, write_control
from core.execution_runtime import ledger_path
from core.execution_ledger import ExecutionLedger

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
load_dotenv(ROOT / ".env.local")
sys.path.insert(0, str(ROOT))

BACKTEST_CSV = Path(os.getenv("DASHBOARD_BACKTEST_CSV", ROOT / "backtest_results.csv"))
WALKFORWARD_CSV = Path(os.getenv("DASHBOARD_WALKFORWARD_CSV", ROOT / "walkforward_metrics.csv"))
TRADE_LOG_CSV = Path(os.getenv("DASHBOARD_TRADE_LOG_CSV", ROOT / "trade_log.csv"))
PAPER_EQUITY_CSV = Path(os.getenv("DASHBOARD_PAPER_EQUITY_CSV", ROOT / "paper_equity.csv"))
STATE_JSON = Path(os.getenv("STATE_FILE", ROOT / "state.json"))
HEARTBEAT_MAX_AGE_SECONDS = int(os.getenv("DASHBOARD_HEARTBEAT_MAX_AGE", "300"))

app = Flask(__name__, static_folder=None)
app.secret_key = os.getenv("DASHBOARD_SESSION_SECRET", "")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.getenv("DASHBOARD_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_login_lock = Lock()
_registration_attempts: dict[str, deque[float]] = defaultdict(deque)
_accounts_lock = Lock()
_bot_process_lock = Lock()
_bot_process: subprocess.Popen[str] | None = None
_bot_log_handle: Any = None


def _accounts_database() -> Path:
    return Path(os.getenv("DASHBOARD_ACCOUNTS_DB", ROOT / "dashboard_accounts.sqlite3"))


def _accounts_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_accounts_database())
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboard_users (
            username TEXT PRIMARY KEY COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return connection


def _accounts_exist() -> bool:
    try:
        with _accounts_lock, _accounts_connection() as connection:
            return connection.execute("SELECT EXISTS(SELECT 1 FROM dashboard_users)").fetchone()[0] == 1
    except sqlite3.Error:
        return False


def _valid_username(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    username = value.strip()
    if not 3 <= len(username) <= 32:
        return None
    if not all(character.isascii() and (character.isalnum() or character in "_.-") for character in username):
        return None
    return username


def _valid_password(value: object) -> str | None:
    if not isinstance(value, str) or not 12 <= len(value) <= 1024:
        return None
    return value


def _is_rate_limited(attempts_by_address: dict[str, deque[float]], address: str) -> bool:
    now = time.monotonic()
    with _login_lock:
        attempts = attempts_by_address[address]
        while attempts and attempts[0] < now - 300:
            attempts.popleft()
        if len(attempts) >= 5:
            return True
        attempts.append(now)
    return False


def _start_session(username: str) -> dict[str, object]:
    session.clear()
    session.permanent = True
    session["authenticated"] = True
    session["username"] = username
    session["csrf"] = secrets.token_urlsafe(32)
    return {"authenticated": True, "csrf": session["csrf"], "username": username}


def _auth_configured() -> bool:
    return bool(
        app.secret_key
        and len(app.secret_key) >= 32
        and (os.getenv("DASHBOARD_PASSWORD_HASH") or _accounts_exist())
    )


def _registration_configured() -> bool:
    return bool(app.secret_key and len(app.secret_key) >= 32)


def _paper_broker_urls_configured() -> bool:
    expected = "https://paper-api.alpaca.markets"
    stock_url = os.getenv("STOCK_TRADING_URL", expected).rstrip("/")
    crypto_url = os.getenv("CRYPTO_TRADING_URL", expected).rstrip("/")
    return stock_url == expected and crypto_url == expected


def _managed_bot_status() -> dict[str, Any]:
    global _bot_process, _bot_log_handle
    with _bot_process_lock:
        process = _bot_process
        if process is not None and process.poll() is not None:
            _bot_process = None
            if _bot_log_handle is not None:
                _bot_log_handle.close()
                _bot_log_handle = None
            process = None
        control = read_control()
        return {
            "running": process is not None,
            "stopping": process is not None and control["stop_requested"],
            "managed_by_dashboard": process is not None,
            "pid": process.pid if process is not None else None,
            "paper_safe": _paper_broker_urls_configured(),
        }


@app.before_request
def require_api_login():
    if not request.path.startswith("/api/"):
        return None
    if request.path in {"/api/health", "/api/auth/login", "/api/auth/register", "/api/auth/status"}:
        return None
    if not _auth_configured():
        return jsonify({"error": "Dashboard authentication is not configured"}), 503
    if not session.get("authenticated"):
        return jsonify({"error": "Authentication required"}), 401
    if request.method != "GET":
        if request.headers.get("X-Orbit-CSRF") != session.get("csrf"):
            return jsonify({"error": "Invalid CSRF token"}), 403
        if request.headers.get("X-Requested-With") != "Orbit" or not request.is_json:
            return jsonify({"error": "JSON request required"}), 400
    return None


@app.get("/api/auth/status")
def auth_status():
    configured = _auth_configured()
    authenticated = configured and bool(session.get("authenticated"))
    return jsonify({
        "configured": configured,
        "authenticated": authenticated,
        "csrf": session.get("csrf") if authenticated else None,
        "registration_available": _registration_configured(),
    })


@app.post("/api/auth/login")
def auth_login():
    if not _auth_configured():
        return jsonify({"error": "Configure dashboard credentials first"}), 503
    if not request.is_json or request.headers.get("X-Requested-With") != "Orbit":
        return jsonify({"error": "JSON request required"}), 400
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid credentials payload"}), 400
    address = request.remote_addr or "unknown"
    if _is_rate_limited(_login_attempts, address):
        return jsonify({"error": "Too many attempts; wait five minutes"}), 429
    username = _valid_username(data.get("username"))
    password = data.get("password", "")
    if not isinstance(password, str) or len(password) > 1024:
        return jsonify({"error": "Incorrect password"}), 401
    account_password_hash = None
    if username:
        try:
            with _accounts_lock, _accounts_connection() as connection:
                row = connection.execute(
                    "SELECT password_hash FROM dashboard_users WHERE username = ?",
                    (username,),
                ).fetchone()
                account_password_hash = row[0] if row else None
        except sqlite3.Error:
            return jsonify({"error": "Account storage is unavailable"}), 503
    legacy_hash = os.getenv("DASHBOARD_PASSWORD_HASH")
    valid_account = bool(account_password_hash and check_password_hash(account_password_hash, password))
    valid_legacy = bool(not username and legacy_hash and check_password_hash(legacy_hash, password))
    if not valid_account and not valid_legacy:
        return jsonify({"error": "Incorrect username or password"}), 401
    with _login_lock:
        _login_attempts.pop(address, None)
    return jsonify(_start_session(username or "local-admin"))


@app.post("/api/auth/register")
def auth_register():
    if not _registration_configured():
        return jsonify({"error": "Configure DASHBOARD_SESSION_SECRET first"}), 503
    if not request.is_json or request.headers.get("X-Requested-With") != "Orbit":
        return jsonify({"error": "JSON request required"}), 400
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or set(data) != {"username", "password"}:
        return jsonify({"error": "Provide a username and password"}), 400
    address = request.remote_addr or "unknown"
    if _is_rate_limited(_registration_attempts, address):
        return jsonify({"error": "Too many attempts; wait five minutes"}), 429
    username = _valid_username(data["username"])
    password = _valid_password(data["password"])
    if not username:
        return jsonify({"error": "Username must be 3-32 characters using letters, numbers, ., _ or -"}), 400
    if not password:
        return jsonify({"error": "Password must be 12-1024 characters"}), 400
    try:
        with _accounts_lock, _accounts_connection() as connection:
            connection.execute(
                "INSERT INTO dashboard_users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.IntegrityError:
        return jsonify({"error": "This username is already registered"}), 409
    except sqlite3.Error:
        return jsonify({"error": "Account storage is unavailable"}), 503
    with _login_lock:
        _registration_attempts.pop(address, None)
    return jsonify(_start_session(username)), 201


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"authenticated": False})


@app.get("/api/bot")
def bot_status():
    return jsonify(_managed_bot_status())


@app.post("/api/bot")
def bot_control():
    global _bot_process, _bot_log_handle
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or data.get("action") not in {"start", "stop"} or set(data) != {"action"}:
        return jsonify({"error": "Expected start or stop action"}), 400
    if data["action"] == "stop":
        status = _managed_bot_status()
        if not status["managed_by_dashboard"]:
            return jsonify({"error": "No dashboard-managed paper bot is running"}), 409
        try:
            request_stop()
        except OSError:
            return jsonify({"error": "Could not request a safe bot shutdown"}), 503
        return jsonify(_managed_bot_status())

    if not _paper_broker_urls_configured():
        return jsonify({"error": "Dashboard start is restricted to Alpaca paper-trading URLs"}), 409
    with _bot_process_lock:
        if _bot_process is not None and _bot_process.poll() is None:
            return jsonify({"error": "The dashboard-managed paper bot is already running"}), 409
        runtime = _runtime_status(_read_state())
        if runtime["status"] in {"online", "paused"}:
            return jsonify({"error": "A paper bot is already running outside this dashboard session"}), 409
        try:
            write_control(paused=True)
            _bot_log_handle = (ROOT / "aether_dashboard_launcher.log").open("a", encoding="utf-8")
            _bot_process = subprocess.Popen(
                [sys.executable, "-m", "scripts.paper_trading.multi_asset_loop"],
                cwd=ROOT,
                stdout=_bot_log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError:
            if _bot_log_handle is not None:
                _bot_log_handle.close()
                _bot_log_handle = None
            _bot_process = None
            return jsonify({"error": "Could not start the local paper bot"}), 503
    return jsonify(_managed_bot_status()), 201


@app.get("/api/control")
def control_status():
    return jsonify(read_control())


@app.post("/api/control")
def control_update():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid control payload"}), 400
    if data.get("action") not in {"pause", "resume"} or set(data) != {"action"}:
        return jsonify({"error": "Expected pause or resume action"}), 400
    try:
        return jsonify(write_control(paused=data["action"] == "pause"))
    except OSError:
        return jsonify({"error": "Control file unavailable; entries remain paused"}), 503


def _clean_json(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json(item) for item in value]
    return value


def _read_csv(path: Path, required: set[str], date_columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, parse_dates=date_columns or [])
    except (OSError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()
    return frame if required.issubset(frame.columns) else pd.DataFrame()


def _read_backtest_df() -> pd.DataFrame:
    frame = _read_csv(BACKTEST_CSV, {"timestamp", "close", "StratReturn"}, ["timestamp"])
    if frame.empty:
        return frame
    frame = frame.sort_values("timestamp").copy()
    frame["strat_return"] = pd.to_numeric(frame["StratReturn"], errors="coerce").fillna(0.0)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if "Position" in frame.columns:
        frame["position"] = pd.to_numeric(frame["Position"], errors="coerce").fillna(0.0)
    frame["equity"] = (1.0 + frame["strat_return"]).cumprod()
    frame["benchmark"] = frame["close"] / frame["close"].iloc[0]
    frame["drawdown_pct"] = (
        (frame["equity"] / frame["equity"].cummax()) - 1.0
    ) * 100
    return frame.dropna(subset=["timestamp", "close"])


def _read_walkforward_df() -> pd.DataFrame:
    dates = ["TrainStart", "TrainEnd", "TestStart", "TestEnd"]
    required = {"CAGR", "Sharpe", "MaxDrawdown", "WinRate", *dates}
    frame = _read_csv(WALKFORWARD_CSV, required, dates)
    if frame.empty:
        return frame
    for column in ("CAGR", "Sharpe", "MaxDrawdown", "WinRate"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["TestStart", "TestEnd", "Sharpe"])


def _read_trade_log_df() -> pd.DataFrame:
    return _read_csv(TRADE_LOG_CSV, set())


def _read_paper_equity_df() -> pd.DataFrame:
    frame = _read_csv(PAPER_EQUITY_CSV, {"timestamp", "equity", "cash"}, ["timestamp"])
    if frame.empty:
        return frame
    for key in ("equity", "cash"):
        frame[key] = pd.to_numeric(frame[key], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "equity", "cash"])
    frame = frame[frame["equity"].map(math.isfinite) & frame["cash"].map(math.isfinite)]
    frame = frame[(frame["equity"] >= 0) & (frame["cash"] >= 0)]
    return frame.sort_values("timestamp").tail(1000)


def _read_state() -> dict[str, Any]:
    if not STATE_JSON.exists() or STATE_JSON.stat().st_size == 0:
        return {}
    try:
        value = json.loads(STATE_JSON.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _iso_timestamp(value: Any) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _runtime_status(state: dict[str, Any]) -> dict[str, Any]:
    control = read_control()
    heartbeat = _iso_timestamp(state.get("last_heartbeat"))
    heartbeat_age = None
    if heartbeat:
        parsed = datetime.fromisoformat(heartbeat)
        heartbeat_age = max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))
    halted = bool(state.get("trading_halted_today", False))
    locked = bool(state.get('execution_uncertain', False))
    approved = os.getenv('PAPER_ENTRIES_APPROVED', 'false').lower() == 'true'
    if halted:
        status = "halted"
    elif (control["paused"] or locked or not approved) and heartbeat_age is not None and heartbeat_age <= HEARTBEAT_MAX_AGE_SECONDS:
        status = "paused"
    elif heartbeat_age is not None and heartbeat_age <= HEARTBEAT_MAX_AGE_SECONDS:
        status = "online"
    else:
        status = "offline"
    return {
        "status": status,
        "last_heartbeat": heartbeat,
        "heartbeat_age_seconds": heartbeat_age,
        "trading_halted_today": halted,
        "entries_paused": control["paused"] or locked or not approved,
        'operator_paused': control['paused'],
        'execution_uncertain': locked,
        'paper_entries_approved': approved,
        'data_issues': state.get('data_issues', {}),
        'external_positions': state.get('external_positions', {}),
        "control_updated_at": control["updated_at"],
    }


def _open_positions(state: dict[str, Any]) -> list[dict[str, Any]]:
    if state.get('execution_schema_version'):
        # Never upgrade legacy cached entry_price into ownership evidence.
        positions=[]
        for row in state.get('managed_positions',[]):
            if isinstance(row,dict) and (_safe_float(row.get('qty')) or 0) > 0:
                positions.append(dict(symbol=row.get('symbol'),qty=row.get('qty'),
                    entry_price=_safe_float(row.get('entry_price')),trailing_high=None,
                    ownership='ledger',broker_quantity_verified=bool(row.get('broker_quantity_verified'))))
        return positions
    entries = state.get("entry_price", {})
    trailing = state.get("trailing_max", {})
    if not isinstance(entries, dict):
        return []
    positions = []
    for symbol, price in entries.items():
        entry_price = _safe_float(price)
        if entry_price is None or entry_price <= 0:
            continue
        trailing_high = _safe_float(trailing.get(symbol)) if isinstance(trailing, dict) else None
        positions.append({
            "symbol": str(symbol),
            "entry_price": entry_price,
            "trailing_high": trailing_high,
        })
    return positions


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax().replace(0, pd.NA)
    drawdown = (equity - running_max) / running_max
    return float(drawdown.min()) if not drawdown.dropna().empty else 0.0


def _backtest_trade_returns(frame: pd.DataFrame) -> list[float]:
    """Aggregate bar returns into completed position-level returns."""
    if frame.empty or "position" not in frame.columns:
        return []
    completed: list[float] = []
    active_position = 0.0
    compounded = 1.0
    for position, bar_return in zip(frame["position"], frame["strat_return"]):
        position = _safe_float(position) or 0.0
        bar_return = _safe_float(bar_return) or 0.0
        if active_position != 0 and position != active_position:
            completed.append(compounded - 1.0)
            compounded = 1.0
        if position != 0:
            compounded *= 1.0 + bar_return
        active_position = position
    # An open terminal position is unrealized, not a completed trade.
    return [value for value in completed if math.isfinite(value)]


def _live_trade_returns(frame: pd.DataFrame) -> list[float]:
    if frame.empty:
        return []
    lowered = {str(column).lower(): column for column in frame.columns}
    if "event_type" in lowered:
        event_type = frame[lowered["event_type"]].astype(str).str.lower()
        frame = frame[event_type.eq("close")].copy()
        if frame.empty:
            return []
    for candidate in ("pnl_pct", "return_pct", "profit_pct"):
        if candidate in lowered:
            values = pd.to_numeric(frame[lowered[candidate]], errors="coerce").dropna()
            if not values.empty:
                # Accept both decimal (0.02) and percent (2.0) conventions.
                scale = 100.0 if values.abs().median() > 1 else 1.0
                return [float(value / scale) for value in values]
    for candidate in ("pnl", "realized_pnl", "net_pnl", "profit"):
        if candidate in lowered:
            values = pd.to_numeric(frame[lowered[candidate]], errors="coerce").dropna()
            if not values.empty:
                # Dollar P&L still supports win/loss and profit-factor metrics.
                return [float(value) for value in values]
    return []


def _trade_statistics(returns: list[float], source: str | None) -> dict[str, Any]:
    if not returns:
        return {
            "available": False,
            "source": None,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate_pct": None,
            "profit_factor": None,
            "average_win_pct": None,
            "average_loss_pct": None,
            "current_streak": 0,
            "current_streak_type": None,
        }
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    breakeven = len(returns) - len(wins) - len(losses)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    last_direction = 1 if returns[-1] > 0 else -1 if returns[-1] < 0 else 0
    streak = 0
    if last_direction:
        for value in reversed(returns):
            if (value > 0) == (last_direction > 0):
                streak += 1
            else:
                break
    percentage_source = source not in {'live-dollar-pnl','paper-ledger-gross-usd'}
    return {
        "available": True,
        "source": source,
        "total_trades": len(returns),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": breakeven,
        "win_rate_pct": (len(wins) / len(returns)) * 100,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "average_win_pct": (sum(wins) / len(wins) * 100) if wins and percentage_source else None,
        "average_loss_pct": (sum(losses) / len(losses) * 100) if losses and percentage_source else None,
        "current_streak": streak,
        "current_streak_type": "win" if last_direction > 0 else "loss" if last_direction < 0 else None,
    }


def _performance_payload(backtest: pd.DataFrame, trades: pd.DataFrame) -> dict[str, Any]:
    live_returns = _live_trade_returns(trades)
    live_source = None
    if live_returns:
        lowered = {str(column).lower() for column in trades.columns}
        live_source = "live-percent-pnl" if lowered.intersection({"pnl_pct", "return_pct", "profit_pct"}) else "live-dollar-pnl"
    backtest_returns = _backtest_trade_returns(backtest)
    trade_returns = live_returns or backtest_returns
    source = live_source if live_returns else "backtest-trades" if backtest_returns else None
    execution = _execution_payload()
    closed_trades = execution.get('closed_trades')
    if execution['available'] and not execution.get('faults') and isinstance(closed_trades, list):
        # Completed owned inventory cycles, never partial-exit checkpoints.
        closed = sorted(
            (row for row in closed_trades if isinstance(row, dict)),
            key=lambda row: (str(row.get('exit_time') or ''), str(row.get('entry_id') or '')),
        )
        if closed:
            trade_returns=[float(row['realized_gross']) for row in closed]
            source='paper-ledger-gross-usd'

    monthly: list[dict[str, Any]] = []
    if not backtest.empty:
        periods = backtest["timestamp"].dt.to_period("M")
        monthly_returns = (1.0 + backtest["strat_return"]).groupby(periods).prod() - 1.0
        monthly = [
            {"month": str(period), "return_pct": float(value * 100)}
            for period, value in monthly_returns.tail(18).items()
        ]
    return {
        "trades": _trade_statistics(trade_returns, source),
        "monthly_returns": monthly,
        "growth_of_10000": float(backtest["equity"].iloc[-1] * 10_000) if not backtest.empty else None,
    }


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else "public, max-age=300"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
        "font-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    return response


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "micro-trading-dashboard", "version": "4.3-stage3",
                    'check': 'http_liveness_only'})


def _execution_payload() -> dict[str, Any]:
    """Read-only SQLite view. No broker calls, no implicit database creation."""
    try:
        payload=ExecutionLedger(ledger_path(STATE_JSON),readonly=True).snapshot()
        payload['available']=True
    except Exception:
        return dict(available=False,blocked=True,orders=[],inventory=[],closed_trades=[],
            faults=[],reason='Execution ledger not initialized or unavailable')
    state=_read_state()
    observed=state.get('execution',{})
    if not isinstance(observed,dict):observed={}
    payload.update(reconciled_at=state.get('execution_reconciled_at'),
        external_positions=observed.get('external_positions',[]),
        position_mismatches=observed.get('position_mismatches',[]),
        read_errors=observed.get('read_errors',[]),
        legacy_review_required=bool(state.get('legacy_review_required')),
        positions_unavailable=bool(observed.get('positions_unavailable',True)))
    payload['blocked']=bool(payload['blocked'] or payload['protection_unverified_symbols'] or
        payload['read_errors'] or payload['position_mismatches'] or payload['positions_unavailable'] or
        payload['legacy_review_required'])
    return payload


@app.get('/api/execution')
def execution():
    return jsonify(_clean_json(_execution_payload()))


@app.get('/api/crypto-exits')
def crypto_exits():
    path=ledger_path(STATE_JSON).with_name('crypto_exit_status.json')
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        timestamp=_iso_timestamp(data.get('checked_at'))
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(timestamp)).total_seconds() if timestamp else None
        return jsonify(dict(available=True,fresh=age is not None and 0<=age<=60,
            checked_at=timestamp,issues=data.get('issues',[]),mode='crypto_exit_only'))
    except Exception:
        return jsonify(dict(available=False,fresh=False,mode='disabled_or_not_initialized'))


@app.get('/api/readiness')
def readiness():
    execution=_execution_payload()
    runtime=_runtime_status(_read_state())
    reasons=[]
    if not execution['available']:reasons.append('execution_ledger_unavailable')
    if execution['blocked']:reasons.append('execution_not_reconciled')
    if execution.get('pending_entries',0):reasons.append('entry_pending')
    if not execution.get('account_bound'):reasons.append('paper_account_not_bound')
    if runtime['status']=='offline':reasons.append('trader_heartbeat_stale')
    timestamp=_iso_timestamp(execution.get('reconciled_at'))
    age=None
    if timestamp:
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(timestamp)).total_seconds()
    if age is None or not 0 <= age <= 900:reasons.append('reconciliation_snapshot_stale')
    if runtime['entries_paused']:reasons.append('entries_paused_or_stage_locked')
    if runtime['trading_halted_today']:reasons.append('daily_loss_halt')
    return jsonify(dict(ready_for_new_entries=not reasons,reasons=reasons,
        note='Local guards only; not broker authorization or a profitability guarantee.'))


@app.get("/api/overview")
def overview():
    backtest = _read_backtest_df()
    walkforward = _read_walkforward_df()
    trades = _read_trade_log_df()
    state = _read_state()
    performance = _performance_payload(backtest, trades)

    backtest_summary: dict[str, Any] = {}
    if not backtest.empty:
        backtest_summary = {
            "bars": int(len(backtest)),
            "start": backtest["timestamp"].iloc[0].isoformat(),
            "end": backtest["timestamp"].iloc[-1].isoformat(),
            "total_return_pct": float((backtest["equity"].iloc[-1] - 1.0) * 100),
            "max_drawdown_pct": _max_drawdown(backtest["equity"]) * 100,
        }

    walkforward_summary: dict[str, Any] = {}
    if not walkforward.empty:
        walkforward_summary = {
            "periods": int(len(walkforward)),
            "avg_cagr_pct": float(walkforward["CAGR"].mean() * 100),
            "avg_sharpe": float(walkforward["Sharpe"].mean()),
            "avg_max_drawdown_pct": float(walkforward["MaxDrawdown"].mean() * 100),
            "avg_win_rate_pct": float(walkforward["WinRate"].mean() * 100),
            "positive_periods": int((walkforward["Sharpe"] > 0).sum()),
        }

    return jsonify(_clean_json({
        "runtime": _runtime_status(state),
        "activity": {
            "daily_order_count": _safe_int(state.get("daily_order_count", 0)),
            "open_positions": len(_open_positions(state)),
            "recorded_trades": int(len(trades)),
            "last_reset_date": state.get("last_reset_date"),
            "account_equity": _safe_float(state.get("account_equity")),
            "account_cash": _safe_float(state.get("account_cash")),
            "daily_pnl": _safe_float(state.get("daily_pnl")),
            "daily_pnl_pct": _safe_float(state.get("daily_pnl_pct")),
            "broker_positions_count": _safe_int(state.get("broker_positions_count", 0)),
            "open_orders_count": _safe_int(state.get("open_orders_count", 0)),
        },
        "backtest": backtest_summary,
        "walkforward": walkforward_summary,
        "performance": performance,
    }))


@app.get("/api/backtest")
def backtest():
    frame = _read_backtest_df()
    if frame.empty:
        return jsonify([])
    output = frame[["timestamp", "close", "strat_return", "equity", "benchmark", "drawdown_pct"]].copy().tail(3000)
    output["timestamp"] = output["timestamp"].map(_iso_timestamp)
    return jsonify(_clean_json(output.to_dict(orient="records")))


@app.get("/api/performance")
def performance():
    return jsonify(_clean_json(_performance_payload(
        _read_backtest_df(),
        _read_trade_log_df(),
    )))


@app.get("/api/paper-equity")
def paper_equity():
    frame = _read_paper_equity_df()
    if frame.empty:
        return jsonify([])
    output = frame[["timestamp", "equity", "cash"]].copy()
    output["timestamp"] = output["timestamp"].map(_iso_timestamp)
    return jsonify(_clean_json(output.to_dict(orient="records")))


@app.get("/api/walkforward")
def walkforward():
    frame = _read_walkforward_df()
    if frame.empty:
        return jsonify([])
    output = frame.copy().tail(250)
    for column in ("TrainStart", "TrainEnd", "TestStart", "TestEnd"):
        output[column] = output[column].map(_iso_timestamp)
    return jsonify(_clean_json(output.to_dict(orient="records")))


@app.get("/api/trades")
def trades():
    frame = _read_trade_log_df()
    if frame.empty:
        return jsonify([])
    return jsonify(_clean_json(frame.tail(200).to_dict(orient="records")))


@app.get("/api/state")
def state():
    value = _read_state()
    return jsonify(_clean_json({
        "runtime": _runtime_status(value),
        "positions": _open_positions(value),
        "daily_order_count": _safe_int(value.get("daily_order_count", 0)),
        "last_reset_date": value.get("last_reset_date"),
        "account_equity": _safe_float(value.get("account_equity")),
        "account_cash": _safe_float(value.get("account_cash")),
        "daily_pnl": _safe_float(value.get("daily_pnl")),
        "daily_pnl_pct": _safe_float(value.get("daily_pnl_pct")),
        "broker_positions_count": _safe_int(value.get("broker_positions_count", 0)),
        "open_orders_count": _safe_int(value.get("open_orders_count", 0)),
    }))


@app.get("/api/config")
def config_view():
    import config as bot_config

    return jsonify({
        "symbol": bot_config.SYMBOL,
        "timeframe": bot_config.TIMEFRAME,
        "stock_watchlist": bot_config.STOCK_WATCHLIST,
        "crypto_watchlist": bot_config.CRYPTO_WATCHLIST,
        "asset_classes": bot_config.ASSET_CLASSES,
        "risk_per_trade": bot_config.RISK_PER_TRADE,
        "stop_loss_pct": bot_config.STOP_LOSS_PCT,
        "take_profit_pct": bot_config.TAKE_PROFIT_PCT,
        "trailing_stop_pct": bot_config.TRAILING_STOP_PCT,
        "max_portfolio_positions": bot_config.MAX_PORTFOLIO_POSITIONS,
        "max_daily_orders": bot_config.MAX_DAILY_ORDERS,
        "max_daily_drawdown_pct": bot_config.MAX_DAILY_DRAWDOWN_PCT,
        "market_hours_only": True,
        "paper_trading": (
            bot_config.STOCK_TRADING_URL.rstrip("/") == "https://paper-api.alpaca.markets"
            and bot_config.CRYPTO_TRADING_URL.rstrip("/") == "https://paper-api.alpaca.markets"
        ),
    })


@app.get("/")
@app.get("/<path:path>")
def static_files(path: str = "index.html"):
    target = STATIC_DIR / path
    return send_from_directory(STATIC_DIR, path if target.is_file() else "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("DASHBOARD_PORT", "8080")), debug=False)
