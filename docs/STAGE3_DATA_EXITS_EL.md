# Stage 3 — timeframes και crypto exit supervisor

Ελεγμένο offline checkpoint, όχι ακόμη unattended paper/live release.
Διατηρούνται το Orbit UI και όλες οι προηγούμενες διορθώσεις.

## Market data

- CryptoCompare: direct legacy REST requests, key μόνο σε Authorization header,
  όχι στο URL. Base minute/hour/day bars, local ακριβής OHLCV aggregation στο
  ζητούμενο timeframe. `5min` δεν επιστρέφει ωριαία δεδομένα.
- UTC-aware timestamps, πλήρεις aggregate bars μόνο, bounded backward pagination,
  exact quote currencies (USDT/USDC δεν μετατρέπονται σε USD), conflicting-overlap
  και gap rejection. Minute lookback πάνω από 7 ημέρες απορρίπτεται ρητά· δεν
  επιστρέφεται σιωπηρά truncated dataset. Η πρόσβαση εξαρτάται και από provider plan.
- Stock Polygon/Massive: exact intraday multiplier/timespan, UTC millisecond ranges,
  `next_url` pagination με ίδιο εγκεκριμένο host, όχι silent timeframe fallback.
  Default host `api.massive.com`, προαιρετικά `STOCK_DATA_HOST=api.polygon.io`.
- Keys στο header, connect/read timeout 5/20s, redirects off, έως 20 pages,
  process-local monotonic rate limit: stock 12s, crypto 1s. Δεν είναι καθολικό
  account-wide quota limiter. HTTP/rate-limit failure απορρίπτει fetch χωρίς
  επιστροφή μισού dataset ή raw error/secret-bearing URL.
- Stock daily/multi-day bars απορρίπτονται **πριν** το HTTP: απαιτούν ET/calendar
  session-close policy. Δεν ισχυριζόμαστε ότι fixed UTC day αποδεικνύει κλειστό
  stock daily candle. Stock session gaps, split/corporate-action consistency,
  entitlement/recency και archive dataset coverage παραμένουν research θέματα.

Provider contracts ελέγχθηκαν με fake HTTP responses, όχι πραγματικά κλειδιά.
Δεν έχει επιβεβαιωθεί production response compatibility/entitlement στον λογαριασμό σου.

## Crypto exits

Υλοποιήθηκε ανεξάρτητος **exit-only process**, όχι δεύτερη strategy loop/thread.
Δεν εισάγει historical feeds ή indicators. Έτσι feed waits, bar sleep και strategy
errors στο trader δεν εμποδίζουν τον supervisor να εκτελέσει τον δικό του κύκλο.
Η πολιτική exits δεν εξαρτάται από entry pause, daily-loss halt ή bearish signal.

- Απαιτεί ledger-owned crypto entry, pinned exit policy και settled buy order.
  Δεν υιοθετεί παλιές/manual θέσεις και δεν δημιουργεί DB όταν λείπει το υπάρχον ledger.
- Broker bid/ask quote: θετικές finite τιμές, όχι crossed quote, όχι future timestamp,
  μέγιστη ηλικία 10s. Χρησιμοποιείται bid για long-exit decision, όχι last candle close.
- Fixed stop, persisted high-water trailing stop, full take-profit και μία
  partial-take προσπάθεια ανά inventory cycle. Partial qty στρογγυλοποιείται προς τα κάτω.
- Policy και high water αποθηκεύονται στο SQLite. Restart δεν μηδενίζει trailing
  history και δεν αλλάζει σιωπηρά την pinned policy.
- Exit intent commit πριν το POST, stable client ID, pending-exit guard και
  GET-only recovery. Timeout/404 δεν οδηγούν σε δεύτερη exit υποβολή.
- Broker position quantity και conflicting symbol orders ελέγχονται ξανά
  αμέσως πριν το sell. Δεν ανοίγονται shorts. Requests παραμένουν paper-only,
  market/GTC, με bounded timeout και SDK retries off.
- Confirmed exit fills ενημερώνουν το υπόλοιπο owned inventory. Partial exit
  δεν γίνεται completed trade μέχρι να κλείσει όλη η θέση. Gross P&L μόνο.
- Account/order/quarantine/quantity errors παραμένουν fail-closed. Η απουσία
  crypto broker bracket από μόνη της δεν μπλοκάρει μια απαιτούμενη software exit.
- Ξεχωριστό supervisor runtime lock αποτρέπει δύο exit processes στο ίδιο volume.
  Status JSON γράφεται atomic/fsync και εμφανίζεται read-only στο dashboard.

## Schema και lifecycle

Schema v2 migration διατηρεί τα stage-2 stock orders/IDs. Δεν δημιουργεί crypto
ownership ή policies από παλιά JSON/state. Crypto prepare-entry απαιτεί explicit
asset class και έγκυρη pinned exit policy πριν από το intent commit.
Η κύρια strategy runtime εξακολουθεί να έχει **crypto entries disabled**: δεν
ανοίγουμε νέες crypto θέσεις πριν γίνει ελεγχόμενη paper integration.

Migration έχει offline test με synthetic v1 DB. Πριν πραγματική migration απαιτείται
backup και σταματημένοι writers. Με δύο processes, ασυνεπή/out-of-order broker
snapshots μπορεί να οδηγήσουν σε conservative quarantine· streaming/event-level
reconciliation και coordinated historical polling απομένουν.

## Off by default — δεν ξεκινάμε supervisor τώρα

Compose service `crypto-exit-supervisor` βρίσκεται στο profile `crypto-exits`,
με `restart: no` και `ENABLE_CRYPTO_EXIT_SUPERVISOR=false` ως hard-coded environment.
Άρα default Compose start δεν το ενεργοποιεί. Δεν αρκεί να αλλάξεις μόνο `.env.local`.
Δεν δίνουμε ακόμη εντολή ενεργοποίησης: απαιτεί ξεχωριστό controlled paper validation.
Νέες entries παραμένουν locked by default. Manual/legacy θέσεις ελέγχονται από εσένα
στον broker, όχι από τον καινούργιο supervisor.

## Όρια που δεν κρύβουμε

Software stop δεν προστατεύει σε process/host/Docker/network outage. Quote API failure
οδηγεί σε issue και όχι guessed exit price. Market exit δεν εγγυάται συγκεκριμένο
fill price ή maximum loss. Minimum crypto order size/dust και fees δεν έχουν ακόμη
επικυρωθεί με broker integration. Partial-take attempt που απορρίπτεται δεν επαναλαμβάνεται
αυτόματα· full-stop/take decision μπορεί να ξαναξιολογηθεί μετά από explicit terminal
rejection/cancellation, όχι μετά από uncertain outcome.

Ο supervisor αναμένει 5s **μετά** τον κύκλο: συνολική latency περιλαμβάνει τα broker
requests και ιστορική reconciliation. Δεν ισχυριζόμαστε εγγυημένη έξοδο ανά 5s.
Large-ledger bounded active polling, authoritative execution IDs, corrections,
replacements, fee reconciliation και production observability παραμένουν ανοιχτά.

## Επαλήθευση

`python -m pytest tests_safe -q`: **194 passed**.
Tests: exact 5min crypto bars/pagination/gaps, header auth/host restriction/timeout,
stop/take/trailing/partial lifecycle, restart/pending/uncertainty, crossed/stale quotes,
same-symbol manual quantity mismatch, adapter long-only checks και v1→v2 migration.
Network connections μπλοκάρονται στις offline tests. Δεν χρησιμοποιήθηκαν credentials,
δεν έγινε broker request/order, Docker build ή browser visual QA.

## Πηγές API συμβολαίου

- [Massive — Custom Bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- [Alpaca REST SDK](https://github.com/alpacahq/alpaca-trade-api-python/blob/master/alpaca_trade_api/rest.py)
- [CryptoCompare legacy documentation](https://developers.coindesk.com/documentation/legacy/Historical/dataHistominute)
  (η δημόσια σελίδα δεν απέδωσε αναγνώσιμο schema εδώ· οι legacy payloads ελέγχθηκαν
  με fixtures και απαιτούν πραγματική compatibility validation πριν ενεργοποίηση).

Επόμενο στάδιο: ενιαίος causal research/walk-forward pipeline, reproducible dataset
και ablation. Δεν έχουν ολοκληρωθεί όλα τα 13 θέματα ούτε έχει αποδειχθεί trading edge.
