# Technical review — portfolio edition

> Current checkpoint: calendar-aware DAY session modeling. See
> `docs/STAGE7_SESSIONS_EL.md`. Historical profitability numbers are not results
> of this new model. Runtime order lifetime remains unchanged, not re-protected.

> Stage 4 is the current offline research checkpoint. Read `docs/STAGE4_RESEARCH_EL.md`.
> The historical review below is not a new performance assessment; real-data edge,
> trained-model walk-forward validation and account integration remain unverified.

> Current release: stage 3. See `docs/STAGE3_DATA_EXITS_EL.md` (194 passing offline
> tests). This historical report does not describe current supervisor/provider behavior.

> Current release is stage 2. `docs/STAGE2_EXECUTION_EL.md` supersedes this historical
> report. 158 offline tests pass; no broker, Docker build or visual-browser validation.

> **Superseded checkpoint notice:** the text below describes an older release.
> For the current stage-1 changes and current test evidence (94 offline tests),
> use `docs/HARDENING_STATUS_EL.md`. This is not an unattended-trading release.

The supplied archive was inspected and upgraded for an accurate, reviewable paper-trading portfolio presentation. See `docs/PORTFOLIO.md` for publication copy and `README.md` for setup.

## Verified locally

- 41 offline tests passed, including stock/crypto order guards, paper endpoint restrictions, strategy signal fallback, dashboard metrics and malformed input handling.
- Python compilation and JavaScript syntax checks passed.
- Flask static page and health, overview, state, performance, configuration endpoints returned HTTP 200 without keys.
- No broker connection or paper order was attempted in the offline suite.

## Changes from the supplied archive

- Fixed technical buy signals being mathematically unable to pass the confidence threshold with an absent ML model.
- Allowed long-only entries and separated broker stock-clock handling from 24/7 crypto evaluation.
- Rejected non-paper broker hosts; validated crypto GTC/simple order path, symbol translation and whole-share stock brackets.
- Prevented accidental account-wide cancellation of protective bracket orders and fail-closed on unavailable position/order status.
- Marked local entries as submitted orders, not fills; suppressed invented realized P&L from submission events.
- Shared state and control policy between Compose services with a named volume; bound dashboard to local host.
- Added hashed-password dashboard login, scoped session cookies, CSRF checks and pause/resume controls that default to paused. The trader checks controls before each new paper entry while retaining position exit logic.
- Stock positions now use broker average fill prices in the dashboard and retain their broker-managed bracket exits; software closes are reserved for crypto to avoid conflicting with stock bracket legs.
- Added a distinct paper-account equity history sourced from broker account snapshots, independent of backtest performance.
- The two Compose services now start together, restart with Docker, and use separate healthchecks for the HTTP dashboard and trader heartbeat. An offline preflight checks the local paper configuration before the first start.
- Simplified package dependencies and replaced stale placeholder package metadata and nonexistent project URLs.

## Open before unattended paper trading

Broker-confirmed fill reconciliation, recovery after restart, robust treatment of partial fills and canceled orders, and authenticated paper-account integration tests. For crypto, no broker-side bracket stop is present: the loop's exit logic depends on process uptime and timely market data. Open orders block new entries conservatively. Backtesting needs fees, spread, slippage, survivorship controls and a reproducible out-of-sample evaluation before any performance claim. The legacy single-symbol loop and experimental `src/` path have not been brought to the same safety standard. Docker build could not be run here.

Older archives reportedly contained API secrets. Treat any previously exposed credentials as compromised and rotate them before creating a public Git history. This archive contains only `.env.example`, but scan the final Git history separately before publishing.
