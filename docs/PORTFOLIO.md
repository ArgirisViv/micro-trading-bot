# Portfolio presentation

## Suggested LinkedIn project title

Micro Trading Bot — Paper-Trading Research & Monitoring Dashboard

## LinkedIn description (English)

Built a Python paper-trading research project for stocks and crypto with a responsive, authenticated web control center. Implemented technical/optional ML signals, cash-aware position sizing, broker-clock checks for stock entries, order validation and daily risk limits. Integrated an Alpaca paper account with Polygon/CryptoCompare market data and exposed clearly separated backtest analytics and broker-reported paper equity history through Flask. Added an operator pause/resume flow for new paper entries with a fail-closed control file, session login and CSRF checks. Added offline tests for broker guardrails, strategy fallback and dashboard behavior. The project is a prototype for engineering and research; no live-money or profitability claims.

## GitHub summary

Python paper-trading research bot with Alpaca paper-only order validation, technical signals, risk controls and an authenticated Flask control center for pausing/resuming new entries. Offline-tested; live trading and strategy profitability are unverified.

## How to demonstrate honestly

1. Show the password login, then the dashboard and its offline/empty state without exposing real account details.
2. Show an isolated offline test run and the broker safety checks.
3. If you later have genuine paper-account activity, capture a screenshot after removing account identifiers, keys and personal data. Label backtest plots as backtests and broker values as paper account data.
4. Do not publish a win rate or profit figure until it comes from reconciled, completed broker fills over a disclosed sample period.

## Current evidence

- Deterministic offline tests; no real paper order was placed during verification.
- Flask endpoints and the Docker stack (dashboard + paper-trader) were smoke-checked locally and report healthy.
- Authenticated broker integration has not been validated end to end.

