# Stage 2 — execution ledger και reconciliation

## Τι ολοκληρώθηκε

Συνδέθηκε ο ενεργός multi-asset runtime με SQLite execution journal. Το dashboard
διαβάζει το journal μόνο τοπικά/read-only, χωρίς broker requests ή δυνατότητα
υποβολής/ακύρωσης εντολών. Το Orbit UI παραμένει και προστέθηκε execution panel.

- SQLite transactions με `synchronous=FULL`, foreign keys και μοναδικά intent/client/broker IDs.
- Intent commit **πριν** το broker POST. Ίδιο symbol/bar/entry key δεν επανυποβάλλεται,
  ακόμη και μετά από restart. Διαφορετικά parameters στο ίδιο key απορρίπτονται.
- Timeout, 404 lookup ή crash δεν αποτελούν απόδειξη απόρριψης. Παραμένει reservation
  και fail-closed block. Recovery κάνει μόνο GET με το αποθηκευμένο ίδιο client ID.
- Broker parent και nested bracket legs συμφωνούνται σε μία ατομική transaction.
  Sell leg ownership προκύπτει από το parent που επέστρεψε ο broker, όχι από symbol μόνο.
- Fill deltas προκύπτουν από cumulative `filled_qty × filled_avg_price`, αφαιρώντας
  το προηγούμενο cumulative notional. Replay δεν διπλομετρά fills ή P&L.
- Inventory/average-cost basis και realized gross P&L ανά owned entry cycle.
  Partial exits δεν μετριούνται ως ξεχωριστά completed trades.
- Αλλαγή account ID, regressions, fill-price corrections, replacements, διαφορετικό
  symbol/side, invalid numbers ή over-close οδηγούν σε quarantine/lock, όχι guessing.
- Μη συμφωνημένο broker quantity στο ίδιο symbol μπλοκάρει entries. Άλλες προϋπάρχουσες
  θέσεις, όπως NVDA, παραμένουν external και δεν υιοθετούνται/κλείνονται από το bot.
- Ο daily intent counter ανακατασκευάζεται από το ledger, ώστε να επιβιώνει crash
  πριν την αποθήκευση του JSON state. Μετρά conservatively prepared intents, όχι fills.
- Rejected/canceled/expired zero-fill εντολές ελευθερώνουν reservation, αλλά το ίδιο
  intent δεν επαναλαμβάνεται. Canceled partial entry διατηρεί μόνο τη γεμισμένη ποσότητα.
- Reconciliation προηγείται feed/strategy/market-clock gates, και όταν τα entries
  είναι paused. Το bar-wait heartbeat παραμένει liveness, όχι fill/readiness επιβεβαίωση.
- SDK automatic retries είναι off. Broker requests έχουν connect/read timeout 5/20s
  και δεν ακολουθούν redirects. Το compatibility point αφορά `alpaca-trade-api` 3.x.
- `GET /api/execution` και `/api/readiness` είναι authenticated. Readiness δεν σημαίνει
  broker authorization, εγγυημένο protective fill ή κερδοφορία.

## Τι δεν ισχυριζόμαστε

Το ledger καταγράφει **cumulative fill checkpoints**, όχι individual exchange execution
IDs. Τα ποσά είναι broker-derived από reported averages, με την ακρίβεια που επιστρέφει
ο broker. Fees, commissions, interest και corporate actions δεν έχουν συμφωνηθεί.
Το label είναι gross P&L, όχι net ή audited απόδοση.

Quantity matching δεν διακρίνει μια χειροκίνητη πώληση και επαναγορά ίδιας ποσότητας
στο ίδιο symbol. Για πραγματικό ownership isolation απαιτείται dedicated paper account
και απουσία χειροκίνητων συναλλαγών. Replacements και price corrections δεν διορθώνονται
αυτόματα σε αυτό το στάδιο. Quarantine δεν έχει «reset» button.

Το protection check ελέγχει observed active stop/take legs και quantity coverage.
Δεν εγγυάται ότι ένα stop θα γεμίσει στην τιμή του. Canceled partial entry ή missing
bracket protection μπλοκάρουν νέες entries και χρειάζονται review· δεν στέλνουμε
αυτόματα replacement/close order.

Η reconciliation είναι polling στην αρχή κάθε bar cycle, όχι streaming/event-complete
recovery. Τα ξεχωριστά order/position GETs δεν αποτελούν atomic account snapshot:
μια προσωρινή διαφορά μπλοκάρει ενέργειες μέχρι επόμενη συμφωνία. Ιστορικά roots
ελέγχονται επίσης· archival, pagination και large-ledger performance απομένουν.

## Ασφάλεια της παρούσας release

Νέες entries παραμένουν locked by default, ακόμη κι αν το αποθηκευμένο operator
control λέει resume. Μην θέσεις `PAPER_ENTRIES_APPROVED=true` τώρα.
Ο παλιός software crypto close/partial-close κώδικας αφαιρέθηκε από τον ενεργό loop.
Crypto entries/exits θα υλοποιηθούν και θα επικυρωθούν στο επόμενο στάδιο.
Δεν τρέχουμε αυτόν τον trader για να διαχειριστεί ήδη υπάρχουσες crypto θέσεις.

State-1 intent μπορεί να εισαχθεί μόνο με τα ακριβή αποθηκευμένα identifiers/parameters.
Παλιό `submitted_symbols` ενεργοποιεί `legacy_review_required`: δεν «βαφτίζουμε» παλιά
JSON entries σαν επιβεβαιωμένα lots. Αν λείπει ledger που είχε ήδη initialized state,
η αυτόματη αναδημιουργία απορρίπτεται. Μην διαγράφεις state/DB για να φύγει το lock.

## Έλεγχοι — 16 Σεπτεμβρίου 2026

`python -m pytest tests_safe -q`: **158 passed** (94 stage-1 + 64 νέοι/επεκταμένοι έλεγχοι).
Οι offline tests μπλοκάρουν network connections και χρησιμοποιούν fake brokers.
Ελέγχθηκαν runtime integration, SQLite replay/restart/concurrency/rollback,
partial fills/exits, account binding, ownership/protection guards, GET adapters και
authenticated API/gross trade metrics. Δεν πραγματοποιήθηκε πραγματικό broker request
ή order. Δεν έγινε Docker build ή browser visual QA.

## Τεχνικές πηγές συμβολαίου

- [Alpaca — Placing Orders](https://docs.alpaca.markets/us/docs/orders-at-alpaca):
  order identifiers, bracket activation/legs και κίνδυνος fill και των δύο exits.
- [Alpaca Python REST SDK source](https://github.com/alpacahq/alpaca-trade-api-python/blob/master/alpaca_trade_api/rest.py):
  client-ID lookup, nested order GET, retry και transport behavior.

## Επόμενο στάδιο

Provider timeframes/UTC/pagination και fresh execution quotes, μετά ledger-backed
crypto exits ανεξάρτητα από ιστορικά candles/strategy. Έπειτα causal research/walk-forward,
fees/corporate actions και controlled paper integration. Δεν έχουν τελειώσει όλα τα 13.
