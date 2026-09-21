# Hardening checkpoint 1 — 16 Σεπτεμβρίου 2026

> Ιστορικό stage-1 report. Για τις νεότερες εργασίες execution ledger/ownership,
> τους 158 offline ελέγχους και τα υπολειπόμενα όρια, δες `STAGE2_EXECUTION_EL.md`.

Δεν έχουν ολοκληρωθεί και τα 13 θέματα. Αυτό είναι ελεγμένο ενδιάμεσο checkpoint,
όχι τελική release για unattended paper trading ή ανακοίνωση αποδόσεων στο LinkedIn.
Το Orbit UI διατηρήθηκε. Δεν έγιναν πραγματικές συνδέσεις broker, εντολές ή αλλαγές
στον λογαριασμό σου. Δεν χρησιμοποιήθηκαν τα credentials του προηγούμενου ZIP.

## Κατάσταση των 13 ενοτήτων

| # | Ενότητα | Υλοποίηση σε αυτό το checkpoint | Τι απομένει |
| --- | --- | --- | --- |
| 1 | Sizing και stop | Το sizing χρησιμοποιεί το fixed stop, απορρίπτει μη πεπερασμένες τιμές και στρογγυλοποιεί qty προς τα κάτω. Κοινό broker reference για stock sizing/bracket. | Tick rounding, gap/fill risk, συνολικό portfolio risk και exposure caps. Το market fill δεν είναι εγγυημένο reference price. |
| 2 | Ημερήσια όρια | Reset UTC μέσα στο loop, όχι μόνο στην εκκίνηση. | Cash-flow-adjusted drawdown και ολοκληρωμένος calendar/session policy. |
| 3 | Signal lifecycle | Reset προηγούμενου signal μετά από παρατηρημένο κλείσιμο και αποτροπή επανάληψης ίδιας entry bar. | Πλήρες fill-driven state machine και canceled/rejected-order recovery. |
| 4 | Ποιότητα δεδομένων | UTC, ολοκληρωμένα candles, freshness, μοναδικά timestamps, finite OHLCV/range checks. Routing βάσει watchlist αντί substring. | CryptoCompare πραγματικό requested timeframe, pagination/rate limits, stock adjustments, gaps και ακριβής χρονικός συγχρονισμός. |
| 5 | Cash/pending entries | Δεν επαναχρησιμοποιείται το ίδιο cash ανά symbol. Μια υποβολή μπλοκάρει δεύτερη entry στο ίδιο cycle. | Durable reservations με partial fills και buying-power reconciliation. |
| 6 | Order ledger/reconciliation | Durable intent και client order ID πριν το POST. Αβέβαιο αποτέλεσμα κλειδώνει entries και μετά από restart. | SQLite execution ledger, broker-confirmed fills/legs, idempotent reconciliation, πραγματικό realized P&L. Μην αφαιρείς χειροκίνητα το lock. |
| 7 | Ownership θέσεων | Δεν υιοθετούνται αυτόματα pre-existing/manual θέσεις χωρίς καταγραφή υποβολής από το bot. | Ownership ανά order/lot και ανίχνευση χειροκίνητων αλλαγών στο ίδιο symbol. Η λίστα submitted_symbols δεν είναι τελικό ownership model. |
| 8 | Crypto exits | Νέες crypto entries απενεργοποιημένες. | Fresh broker bid/ask exits ανεξάρτητα από strategy/feed, fixed stop/take/trailing και fill-confirmed partial closes. Ο παλιός exit κώδικας παραμένει μη επικυρωμένος. |
| 9 | ML | Άγνωστο τελευταίο label παραμένει NA. Causal features χωρίς fabricated warmup. Purged temporal holdout, schema/metadata, όχι dummy training artifact. ML off by default. | Πραγματικό walk-forward fitting, artifact validity window, probability calibration και profitability baseline. |
| 10 | Regime/macro | Regime adaptation απενεργοποιημένο εξ ορισμού ώστε να μη χρησιμοποιούνται full-window historical labels. | Causal regime implementation και ablation. Macro παραμένει μη λειτουργικό overlay. |
| 11 | Fundamentals | Διόρθωση διπλής αντιστροφής P/E, P/B, debt και normalization στα διαθέσιμα metrics. | Point-in-time πηγή fundamentals, αξιόπιστες μονάδες και ενεργό value filter. Το stub δεν έγινε πραγματική λειτουργία. |
| 12 | Backtesting | Νέος κοινός long-only CSV simulator: next-bar open, bracket stop/take, gap stops, stop-first, assumed costs, κλειστά trades, non-overlapping window helper. | Αντικατάσταση όλων των legacy backtest paths, πραγματικό walk-forward/ablation, session/expiry/partial-fill model και out-of-sample dataset. Δεν έχει αποδειχθεί edge. |
| 13 | Dashboard/Docker/QA | Effective entry lock στο UI/API, terminal ανοικτά trades δεν παρουσιάζονται κλειστά, single-worker login limiter με atomic attempt reservation, runtime lock, fsync και heartbeat στη bar αναμονή. | Persistent limiter, broker readiness/observability, dependency lockfile, Docker build/integration tests και fill-backed metrics. |

## Επαλήθευση

- `python -m pytest tests_safe -q`: **94 passed** στο διαθέσιμο Python 3.12 περιβάλλον.
- Στη βάση πριν τις αλλαγές: 40 passed / 1 failed. Η μία αποτυχία ήταν stale assertion
  για το προηγούμενο UI title· ενημερώθηκε στο πραγματικό Orbit title, όχι αφαιρέθηκε.
- Οι νέες δοκιμές περιλαμβάνουν πραγματικό loop με πλήρως fake broker/feed/clock,
  timeout/restart, intent-before-POST, external positions, duplicate runtime lock,
  candle validation, ML temporal integrity και simulated execution edge cases.
- Δεν έγινε Docker build, browser visual QA ή authenticated Alpaca integration.
- Το synthetic test pass δεν αποτελεί backtest απόδοσης ούτε ένδειξη κερδοφορίας.

## Επόμενη σειρά

1. Execution ledger/reconciliation και ownership ανά fill (6, 7, 3, 5).
2. Provider timeframes/fresh quotes και crypto exits (4, 8).
3. Ενιαίος causal research pipeline, walk-forward και ablation (9–12).
4. Readiness/observability, reproducibility και ελεγχόμενη paper integration (13, 1, 2).
5. Μόνο μετά τα παραπάνω: τελικό review και GitHub/LinkedIn παρουσίαση.

`PAPER_ENTRIES_APPROVED` απουσιάζει επίτηδες από το example configuration: το default
είναι false. Μην το θέσεις true σε αυτή τη φάση. `ENABLE_RESEARCH_ML` επίσης default false.
