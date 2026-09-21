# Checkpoint: regular sessions και DAY bracket lifetime

Το stage 7 είναι offline modeling checkpoint, όχι trader activation ή ολοκλήρωση
όλων των audit θεμάτων. Δεν έγινε πραγματικό API αίτημα, νέα μέτρηση κερδοφορίας,
Docker build ή αλλαγή της live/paper πολιτικής εντολών. Τα προηγούμενα copy folders
παραμένουν ως backups. Δεν περιλαμβάνονται credentials ή raw vendor δεδομένα.

## Γιατί χρειαζόταν

Ο stock trader καλεί `submit_order` χωρίς explicit `time_in_force`, άρα χρησιμοποιεί
το υπάρχον default `day`. Το entry gate ελέγχει broker clock. Η παλιά προσομοίωση
επέτρεπε fills/exits σε όλα τα input sessions και διατηρούσε brackets επ' αόριστον.
Τα +5,84%/−2,52% της πρώτης AAPL ανάλυσης είναι αποτελέσματα **εκείνης της
προσέγγισης**, όχι νέα live-matched απόδοση.

Η Alpaca τεκμηριώνει regular-session DAY order lifetime και bracket TIF day/gtc,
με extended hours unsupported για brackets. Από αυτές τις περιγραφές μοντελοποιούμε
τα μη εκτελεσμένα DAY exits ως expired στο session close. Η θέση δεν πωλείται
αυτόματα: μπορεί να μείνει χωρίς ενεργή προστασία. Η ακριβής πραγματική ακολουθία
leg status transitions πρέπει ακόμη να επαληθευτεί σε ελεγχόμενο paper integration.

Πηγές:
[Alpaca order types, brackets και TIF](https://docs.alpaca.markets/us/docs/orders-at-alpaca),
[Alpaca REST SDK source](https://github.com/alpacahq/alpaca-trade-api-python/blob/master/alpaca_trade_api/rest.py).
Το παλιό SDK repository εμφανίζεται archived· μετάβαση σε maintained SDK παραμένει
ξεχωριστό θέμα, όχι σιωπηρή dependency αλλαγή αυτού του checkpoint.

## Νέο συμβόλαιο simulation

- Explicit calendar export με declared start/end coverage. Δεν υποθέτουμε ότι
  κάθε weekday είναι market day ή ότι κάθε session κλείνει στις 16:00 ET.
- HH:MM broker clocks μετατρέπονται από America/New_York σε UTC με DST.
  Early-close ημερομηνίες προέρχονται από calendar, όχι χειροκίνητο clock filter.
- Regular fills/exits μόνο για bars που περιέχονται **ολόκληρα** σε session.
  Bars που straddle όριο απορρίπτονται. Αποδεκτά έως 30-minute candles· προτιμήστε 5min.
- Indicators υπολογίζονται σε όλα τα input provider bars, όπως η υπάρχουσα feed
  προσέγγιση. Δεν αφαιρούμε σιωπηρά pre/post-market indicator history.
- Entry signal χρειάζεται ακριβώς προηγούμενο contiguous ολοκληρωμένο bar.
  Δεν μεταφέρεται stale signal από προηγούμενη ημέρα ή κενό τιμών.
  Warmup-boundary fill απαιτεί και provenance timestamp τελευταίου warmup signal.
- Exit triggers ελέγχονται έως το τέλος του τελευταίου regular bar. Κατόπιν τα
  ανεκτέλεστα DAY exits λήγουν. Inventory παραμένει, δεν κλείνει, δεν re-protects
  και δεν υπάρχει auto-adoption/auto-exit στο πραγματικό account.
- Equity marked με όλες τις διαθέσιμες τιμές. `unprotected_inventory_bars` μετρά
  close-marked snapshots χωρίς active exits, **όχι** πιστοποιημένες ώρες έκθεσης.
- `expired_protection_events` και `open_inventory_protected` κάνουν το κενό ορατό.
  Δεν επιλέγουμε GTC, OCO renewal ή end-of-day liquidation χωρίς ξεχωριστή απόφαση.

## Άμεσο επόμενο βήμα: μόνο calendar download

Ανοίξτε σε VS Code τον νέο εσωτερικό `micro_trading_bot`, μετά αντιγράψτε εκεί
το υπάρχον `.env.local` ως αρχείο. Μην το ανεβάσετε ή εμφανίσετε.
Χρησιμοποιήστε το ήδη εγκατεστημένο venv του προηγούμενου research εργαλείου:

```powershell
Test-Path .\scripts\download_market_calendar.py
Test-Path .env.local
$researchPython = 'C:\Users\argi1\Downloads\micro_trading_bot_research_data_tools\micro_trading_bot\.venv\Scripts\python.exe'
Test-Path $researchPython
& $researchPython -m scripts.download_market_calendar --start 2025-10-01 --end 2026-06-30 --output .\market_calendar_001.json
```

Και οι τρεις έλεγχοι πρέπει να είναι True. Προσαρμόστε το path μόνο αν ο παλιός
φάκελος μετακινήθηκε. Δεν χρειάζεται pip install για αυτή τη λήψη αν το προηγούμενο
venv έχει ήδη pandas/requests/python-dotenv. Η εντολή κάνει μόνο
`GET https://paper-api.alpaca.markets/v2/calendar`, header-authenticated,
timeout 5/20s, no redirects/retries. Χρησιμοποιεί τα υπάρχοντα Alpaca key/secret
τοπικά και αποθηκεύει μόνο date/open/close και μη ευαίσθητη provenance.
Δεν καλεί orders, positions, close/cancel endpoints ή live account.
Υπάρχον output δεν αντικαθίσταται. Error μπορεί να αφήσει ατελές αρχείο σε τοπικό
write failure· μην το θεωρήσετε επιτυχία. Στείλτε αρχικά το terminal μήνυμα και,
σε επιτυχία, μόνο `market_calendar_001.json`.

## Μελλοντική επανεκτέλεση development audit

Με το calendar διαθέσιμο και το ήδη κατεβασμένο AAPL CSV, ο νέος continuous
diagnostic entrypoint είναι:

```powershell
& $researchPython -m scripts.backtesting.session_audit .\research_data_AAPL_001\bars.csv --calendar .\market_calendar_001.json --development-end 2026-06-30 --timeframe 5min --symbol AAPL --output .\session_audit_AAPL_001
```

Δεν χρειάζεται να το τρέξετε ακόμη. Δεν περιλαμβάνουμε το CSV στο ZIP· μεταφέρετέ
το δικό σας αρχείο μόνο όταν χρειαστεί. Το audit προσομοιώνει το development μέχρι
30 Ιουνίου, με base και stress costs, και δεν αξιολογεί τη μεταγενέστερη απόδοση.
Η χρονική επιλογή παραμένει κρίσιμη: μην μετακινήσετε το development end μέσα
στο reserved July–September holdout για tuning.

Τα τέσσερα canonical independent-window CLIs απαιτούν πλέον explicit `--calendar`
ή explicit `--legacy-all-sessions`. Το δεύτερο επιτρέπει μόνο ιστορική approximation.
Το generic independent-window CLI **δεν** κάνει αυτόματο holdout split: μην
του δώσετε ολόκληρο το AAPL CSV για αξιολόγηση του reserved period. Προτιμήστε
το development-only `session_audit` παραπάνω για τον επόμενο έλεγχο.

## Τι παραμένει διαφορετικό από τον trader

Ο simulator είναι single-symbol, instant-full-fill OHLC μοντέλο. Δεν μοντελοποιεί
daily order limits, signal-edge cache, multi-asset allocation, liquidity, latency,
auctions, partial fills ή πραγματικά cumulative broker fills. Το freshness check
είναι συντηρητικό, όχι πλήρες ισοδύναμο όλων των runtime gates.
Τα brackets εξακολουθούν να ορίζονται από simulated fill, όχι ιστορικό broker
pre-submit quote (που δεν υπάρχει στο uploaded OHLC dataset), και δεν αναπαράγουν
όλα τα tick/acceptance constraints. Αυτό είναι γνωστή, μη διορθωμένη απόκλιση·
δεν κατασκευάζουμε ανύπαρκτα historical quotes για να ισχυριστούμε exact alignment.
Η calendar κάλυψη είναι self-described από το export, όχι κρυπτογραφικά πιστοποιημένη.
Το μοντέλο δεν υποκαθιστά πραγματικό paper lifecycle test.

Στο runtime ο ledger ήδη ελέγχει προστασία και μπλοκάρει νέες entries όταν δεν
επιβεβαιώνεται. Αυτό **δεν** επαναφέρει χαμένα protective exits ή μειώνει αυτόματα
την έκθεση. Όλοι οι traders/supervisors παραμένουν stopped/disabled.

## Επαλήθευση

255 offline tests: session fills, no extended-hour exits, DAY expiry χωρίς fake
liquidation/rearm, early closes, holiday omission, DST, missing-bar signals,
warmup timestamp provenance, calendar rejection, mocked read-only export,
prefix invariance, neutral technical-branch equivalence και development-only CLI.
Το suite μπλοκάρει network. Δεν έγινε πραγματικό calendar fetch ή broker integration.

Το NumPy timedelta warning της λήψης αντιμετωπίστηκε με explicit minutes/hours
στο exporter. Offline provider imports έγιναν lazy, ώστε research validators να
μην φορτώνουν credentials/config. Αυτές οι αλλαγές δεν ενεργοποιούν runtime services.
