# Στάδιο 4 — Offline research checkpoint

Αυτό το checkpoint ενοποιεί την αξιολόγηση **σταθερών τεχνικών κανόνων**.
Δεν αποδεικνύει κερδοφορία, δεν ολοκληρώνει τα 13 θέματα της αξιολόγησης και
δεν ενεργοποιεί trading. Δεν περιλαμβάνει walk-forward εκπαίδευση ML.

## Τι άλλαξε

- Όλα τα entrypoints `scripts.backtesting.{offline_backtest,backtest,backtest_walkforward,advanced_backtest}`
  χρησιμοποιούν το ίδιο CSV-only CLI. Οι παλιές online Python signatures αφαιρέθηκαν σκόπιμα.
- Μοναδικά, ήδη ταξινομημένα timezone-aware timestamps, έγκυρο OHLCV και μόνο
  ολοκληρωμένα bars. Naive/future/duplicate timestamps απορρίπτονται.
- Warmup χωρίς συναλλαγές και ανεξάρτητα, μη επικαλυπτόμενα test windows.
  Το τελευταίο warmup signal μπορεί να εκτελεστεί στο πρώτο test open, όχι νωρίτερα.
- Σύγκριση enhanced technical, αφαίρεσης του volume-confirmation gate,
  SMA 10/30, always-long με ίδια brackets/risk sizing, cash και buy-and-hold.
- Ίδια υποθετικά fee/slippage rates και αρχικό κεφάλαιο ανά fold. Buy-and-hold
  είναι πλήρως επενδεδυμένο, άρα **όχι** exposure-matched με τις στρατηγικές.
- Report με dataset/source SHA-256, dependency versions, χρονικά όρια,
  μη αξιολογημένες τελευταίες γραμμές, equity curves και closed-trade CSV ανά fold.
  Υπάρχων output φάκελος δεν αντικαθίσταται.

## Εκτέλεση μόνο για offline έρευνα

Από τον φάκελο που περιέχει `docker-compose.yml`, με τις project dependencies εγκατεστημένες:

```powershell
python -m scripts.backtesting.offline_backtest .\historical_bars.csv --timeframe 5min --symbol AAPL --warmup-bars 100 --test-bars 100 --output .\research_run_001
```

Το CSV πρέπει να έχει `timestamp,open,high,low,close,volume`.
Παράδειγμα timestamp: `2025-01-02T14:30:00Z` (bar **start**).
Το αρχείο δεδομένων δεν παρέχεται ούτε λαμβάνεται από broker με αυτή την εντολή.
Τα counts είναι **bars**, όχι ημέρες. Αν ο output φάκελος υπάρχει, επιλέξτε νέο όνομα.
Δοκιμάστε διαφορετικά κόστη με `--fee-bps` και `--slippage-bps`, χωρίς να επιλέγετε
εκ των υστέρων την πιο ευνοϊκή εκδοχή ως δήθεν ανεξάρτητη επιβεβαίωση.

## Πώς διαβάζουμε τα αποτελέσματα

Τα folds ξεκινούν flat με ίδιο κεφάλαιο. Δεν μεταφέρουν open inventory και
δεν αποτελούν συνεχές portfolio. **Δεν πολλαπλασιάζουμε τις fold returns** ως
deployable compounded return. Open quantities παραμένουν marked-to-close,
δεν γίνονται τεχνητές closed trades. Win rate/profit factor βασίζονται σε πραγματικές
κλεισμένες simulated συναλλαγές, όχι σε θετικά bars. Profit factor χωρίς ζημιές
είναι `null`, όχι ανεξάρτητη απόδειξη άπειρου πλεονεκτήματος.

Η αφαίρεση του volume gate είναι απομονωμένη αλλαγή κανόνα, αλλά διαφορά στο P&L
δεν αποδεικνύει στατιστική αιτιότητα. SMA-only αλλάζει ολόκληρη οικογένεια κανόνων.
Οι προκαθορισμένοι κανόνες δεν κάνουν fitting, συνεπώς warmup δεν ονομάζεται training.
ML/regime/fundamentals/macro αποκλείονται ρητά και δεν φορτώνεται μοντέλο από δίσκο.

## Όρια και επόμενη εργασία

Offline verification: 216 tests, συμπεριλαμβανομένων prefix invariance, αλλαγής
μελλοντικού fold, dataset rejection, κόστους baseline και πραγματικής εκτέλεσης
και των τεσσάρων CSV-only CLI aliases. Το test suite μπλοκάρει broker/provider
network calls. Τα tests ελέγχουν συμπεριφορά κώδικα, **όχι** επενδυτική απόδοση.

- Session calendars, corporate actions, survivorship, vendor adjustments και πληρότητα
  δεδομένων δεν πιστοποιούνται. Το discontinuity count είναι προειδοποίηση, όχι gap repair.
- OHLC intrabar διαδρομή άγνωστη: και τα δύο brackets touched → stop-first.
  Δεν προσομοιώνονται DAY expiry, broker latency, partial fills, fees του πραγματικού
  λογαριασμού ή spread/ρευστότητα. Brackets από simulated fill, live stock brackets
  από pre-submit quote: γνωστή απόκλιση.
- Ο engine είναι stock-style long-only fixed-bracket μοντέλο, **όχι** simulator
  της crypto trailing/partial exit policy του σταδίου 3.
- Χρειάζονται πραγματικό ανεξάρτητο dataset, μεγαλύτερες περίοδοι/πολλά assets,
  sensitivity/stress analysis και κλειδωμένο final holdout πριν από οποιονδήποτε edge claim.
- Purged walk-forward fitting/calibration ML και causal regime overlays παραμένουν
  ξεχωριστή, μη ολοκληρωμένη εργασία. Δεν βαφτίζουμε αυτό το checkpoint ML validation.

Trader και crypto supervisor παραμένουν stopped/disabled. Μην τρέξετε generic
`docker compose up`, `Start-Orbit` ή approval flags για να δοκιμάσετε research.
