# Micro Trading Bot · Paper Trading

> **Current checkpoint: session-aware DAY modeling.** Read
> [session protocol and next steps](docs/STAGE7_SESSIONS_EL.md). Explicit broker
> calendar, regular-session fills, visible DAY protection expiry, continuous
> development-only audit and read-only calendar export. 255 offline tests.
> No new AAPL return claim, broker activation or automated re-protection.
> Earlier checkpoint banners below are historical. Legacy research CLI calls
> now require `--calendar` or explicit `--legacy-all-sessions`.

> **Current addition: read-only historical-data exporter.** Start with
> [download instructions](docs/DOWNLOAD_RESEARCH_DATA_EL.md). Stage-4 research
> protocol is unchanged. No real API download, edge validation or trading activation
> was performed while preparing this copy. Earlier banners below are historical.

> **Current checkpoint: stage 4.** See [research protocol](docs/STAGE4_RESEARCH_EL.md)
> and [monitoring-only migration](docs/MIGRATION_STAGE4_EL.md). Unified offline
> fixed-rule evaluation with non-overlapping windows, baselines and a volume-gate
> ablation. No ML walk-forward training, profitability proof or broker activation.
> Checkpoint banners below are historical; stage 4 supersedes legacy backtest CLIs.

> **Current checkpoint: stage 3.** Read `docs/STAGE3_DATA_EXITS_EL.md` and
> `docs/MIGRATION_STAGE3_EL.md`. Providers and an independent ledger-backed crypto
> exit supervisor are offline-tested (194 tests), not account-integration validated.
> Entries remain locked; crypto entries and supervisor startup remain disabled.
> Stage-1/2 descriptions below are historical. Stock daily live bars explicitly
> require a later session-close policy rather than silently falling back to 5min.

> **Current checkpoint: stage 2.** Start with `docs/STAGE2_EXECUTION_EL.md` and
> `docs/MIGRATION_STAGE2_EL.md`. Durable SQLite reconciliation is implemented and
> offline-tested; broker integration is not verified. New entries remain locked.
> Legacy software crypto exits were removed from the primary runtime pending stage 3.
> Earlier stage-1 notes below are historical, not the current feature specification.

> **Hardening stage 1 — monitoring/research checkpoint, not unattended trading.**
> Read `docs/HARDENING_STATUS_EL.md` and `docs/MIGRATION_STAGE1_EL.md` first.
> New entries are locked by default, including when a saved operator control says resume.
> Crypto entries and default ML/regime overlays are disabled pending validation.
> The supported offline backtest is `python -m scripts.backtesting.offline_backtest INPUT.csv`.
> Older backtest scripts and experimental modules are not validated performance evidence.

A Python portfolio project for **paper trading** US stocks and crypto with an authenticated web control center branded **Orbit**. It combines technical signals with an optional locally trained ML model, sizes positions against account cash and a risk budget, and submits orders to an Alpaca **paper** account. It is a software engineering and strategy research project; it has no independently verified profitability record.

## What works

- Long-only entries from the multi-asset strategy; a bearish signal does not open a short position.
- Technical signals continue to work when no trained ML artifact is present.
- Alpaca's market clock gates stock entries; crypto can be evaluated around the clock.
- Whole-share stock market entries with stop-loss and take-profit bracket legs; fractional crypto market orders use GTC, without broker-side bracket protection.
- Stock exits are left to the broker's bracket legs; the software trailing/partial exit path is limited to crypto. Displayed position entry prices come from the broker's average fill price when a position is observed.
- Cash-capped sizing using the actual fixed-stop policy, a UTC daily reset, daily drawdown halt, order cap and position cap. ATR is diagnostic, not the sizing stop.
- A responsive Flask dashboard for account snapshots, heartbeat, submitted orders, backtest curves, walk-forward summaries and source-labeled win-rate metrics.
- A separate time-series chart of broker-reported paper-account equity and cash snapshots. Raw account equity can change because of deposits or withdrawals, so the chart is not a verified strategy-return curve.
- Password-protected operator access with a server-side session, CSRF protection and controls to pause/resume **new entries only**. Missing or corrupt controls default to paused. Existing positions can still be managed by the running loop.
- A paper-endpoint guard that refuses live or lookalike broker URLs.

**Order submission is not a fill.** The activity log stores submitted orders with signal prices, not confirmed executions or realized P&L. The dashboard shows a paper-trade win rate only if a separately provided trade file contains genuine completed fills and P&L; otherwise it labels trade statistics as backtest-derived or unavailable. Backtests are illustrative and include no verified fee, slippage or latency model.

## Quick start

Requires Python 3.11+.

```bash
cd micro_trading_bot
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install 'pytest>=7.4,<9'
python -m pytest -q
cp .env.example .env.local
# Generate a password hash and session key; copy its output into .env.local:
python -m scripts.prepare_dashboard_auth
python -m webapp.server
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` and copy the example with `Copy-Item .env.example .env.local`. If Windows blocks the `pip.exe` launcher, use `& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt` from inside `micro_trading_bot`.

Add the two generated `DASHBOARD_*` values to `.env.local` and open <http://127.0.0.1:8080>. Without these settings the data API refuses access. Sign in with the password you chose. The first-run entry policy is **paused**; click **Allow entries** only when you are ready to let a running paper trader open new positions. The dashboard itself does not launch a process or place an order.

The command below is the runtime entry point, **not a recommendation to enable trading during this hardening stage**. Keep the old trader stopped and use the monitoring-only migration guide:

```bash
python -m scripts.paper_trading.multi_asset_loop
```

No paper order is sent until the broker account and market-data providers are configured and a strategy signal passes the risk checks. Start with a dedicated paper account and observe it while testing. The default stock feed uses Polygon; crypto data uses CryptoCompare. Provider symbols (`BTCUSD`) are mapped to Alpaca broker pairs (`BTC/USD`) when submitting or querying crypto orders.

## Docker

Create `.env.local` with the dashboard password hash/session secret, newly issued Alpaca **paper** credentials and the market-data keys for the asset classes you enabled. With Docker Desktop running, initialize both containers **once** from the `micro_trading_bot` directory:

```bash
python -m scripts.check_docker_config
docker compose up --build --detach
docker compose ps
```

On Windows, `Start-Orbit.ps1` runs those checks and commands from the project folder. Both services use Docker's `unless-stopped` restart policy: after they have started successfully, opening Docker Desktop again restarts them without running Compose each time. If you intentionally stop a container or run `docker compose down`, start the stack again with `docker compose up -d`. Docker Desktop's **Settings → General → Start Docker Desktop when you sign in** setting is optional if you also want Docker Desktop to open at Windows sign-in.

The saved entry-control state survives restarts. Initially it is **paused**. If you previously clicked **Allow entries**, reopening Docker Desktop can allow the trader to submit new **paper** orders once its risk checks pass; click **Pause entries** before shutting Docker down if you want it to reopen idle. The `paper-trader` container's healthcheck measures loop heartbeat, not broker authorization or profitability.

The dashboard binds to `127.0.0.1:8080` on the host. Both containers use the same named volume for state, order-submission records and the operator control file. The dashboard exposes only pause/resume writes through the application API; there is no endpoint that places an order. The user interface requires a password. To access it remotely, use an authenticated SSH tunnel or another protected access layer; do not expose the dashboard directly to the public internet.

The paper trader also stores broker-reported equity snapshots in the shared volume. These appear in **Equity over time** after an account read succeeds. The chart remains empty until the paper trader runs with valid credentials and market-data configuration.

## Architecture

| Area | Purpose |
| --- | --- |
| `data/` | Polygon and CryptoCompare feed adapters |
| `core/enhanced_strategy.py` | Indicators, optional ML, composite signals |
| `core/alpaca_trade.py` | Paper broker boundary and order validation |
| `scripts/paper_trading/multi_asset_loop.py` | Paper strategy, state, risk limits and submissions |
| `webapp/` | Read-only monitoring API and browser interface |
| `scripts/backtesting/` | Research and walk-forward scripts |
| `src/` | Experimental parallel architecture, not the primary runtime |
| `tests_safe/` | Isolated offline tests; no real broker orders |

## Status and limits

The stage-1 changes override older behavior descriptions above: external positions are not auto-adopted, uncertain submissions lock subsequent entries durably, and a Linux file lock prevents two traders sharing a volume. The Docker dashboard uses one worker so its in-memory login limiter is not split across processes. Runtime state corruption refuses automatic reset. New canonical offline simulation includes configurable assumed fees/slippage, conservative stop-first handling and completed-trade accounting, but does not emulate queueing, partial fills, DAY-bracket expiration or broker execution. Simulated assumptions are not verified costs.

This is a **portfolio-quality paper-trading prototype**, not a live-money system. The tests are offline and do not establish a profitable strategy or validate broker integration. Operator pause prevents new entries at the next control check, but does not guarantee an in-flight submission can be canceled. Resume does not bypass the drawdown halt, order cap or broker checks. The loop still needs broker fill reconciliation and restart recovery before unattended use; submitted orders may be rejected or partially filled. Crypto has no broker-side bracket protection, and its software exit logic only runs while the loop and data feeds are healthy. Stock bracket prices use the last quote at submission and may differ from the actual entry fill. Open broker orders conservatively block new entries. The legacy single-symbol loop in `scripts/paper_trading/paper_trading_loop.py` and experimental `src/` path are not the supported paper runtime.

For any old copy that contained real API credentials, rotate those credentials before publishing. `.env.local`, logs, model artifacts and trading state must stay out of Git. Never load a model from an untrusted pickle/joblib file.
