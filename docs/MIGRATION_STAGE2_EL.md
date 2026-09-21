# Μετάβαση stage 2 — αρχικά μόνο dashboard

Διατήρησε το παλιό project και το named runtime volume. Το ZIP είναι καθαρός κώδικας:
δεν περιέχει `.env.local`, credentials, database, logs ή state. Αντέγραψε το δικό σου
configuration μόνο τοπικά ως αρχείο `.env.local`, όχι φάκελο, χωρίς να το ανεβάσεις.

1. Από τον **παλιό** σωστό project folder, σταμάτησε μόνο τον trader:

```powershell
docker compose -p micro_trading_bot --env-file .env.local stop paper-trader
```

2. Αποσυμπίεσε το νέο ZIP σε ξεχωριστό φάκελο και μπες στον εσωτερικό `micro_trading_bot`.
Κράτησε backup του προηγούμενου project/configuration. Μην κάνεις `down -v`.

3. Από τον νέο folder, αφού έχεις αντιγράψει το δικό σου configuration:

```powershell
Test-Path docker-compose.yml
Test-Path .env.local
python -m scripts.check_docker_config
docker compose -p micro_trading_bot --env-file .env.local config --quiet
docker compose -p micro_trading_bot --env-file .env.local up -d --build --no-deps dashboard
docker compose -p micro_trading_bot --env-file .env.local ps --all
```

Περιμένουμε dashboard running και paper-trader stopped. Άνοιξε `http://localhost:8080`.
Χωρίς αρχικοποιημένο execution DB, το νέο panel σωστά γράφει **NOT INITIALIZED**.
Δεν δημιουργεί demo fills ή fake data. Ο stopped trader σωστά εμφανίζεται offline
μόλις παλιώσει το heartbeat. Το resume παραμένει locked.

Μην εκτελέσεις γενικό `up -d`, `Start-Orbit.ps1` ή trader start τώρα. Δεν έχει γίνει
controlled account integration. Το stop container δεν κλείνει θέσεις και δεν
ακυρώνει protective orders στον paper account. Οι υπάρχουσες θέσεις απαιτούν δικό σου
έλεγχο στο broker dashboard, ιδίως αν υπάρχουν crypto/software-managed exits.

## Offline verification

Σε virtual environment με dependencies και pytest:

```powershell
python -m pytest tests_safe -q
```

Read-only inspection γνωστού υπάρχοντος DB (δεν δημιουργεί νέο DB/network request):

```powershell
python -m scripts.execution_status --db C:\path\execution.sqlite3
```

Το Docker DB path, όταν μελλοντικά αρχικοποιηθεί ο νέος trader με ελεγχόμενη δοκιμή,
είναι `/app/runtime/execution.sqlite3`, στο ίδιο volume με control/state. Μην αντιγράφεις
ένα SQLite DB ενώ γράφεται χωρίς SQLite backup ή πρώτα να σταματήσεις τον writer.
Μην κοινοποιήσεις database/export/state: περιέχουν ιδιωτική trading δραστηριότητα.

Αν εμφανιστεί `legacy_review_required`, `account_mismatch` ή quarantine, δεν καθαρίζουμε
state/faults με το χέρι. Πρώτα γίνεται review της συμφωνίας account/orders/positions.
