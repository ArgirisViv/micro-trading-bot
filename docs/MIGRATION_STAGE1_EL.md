# Ασφαλής δοκιμή του checkpoint

Αυτό το ZIP είναι checkpoint για monitoring και offline tests. Δεν είναι η τελική
έκδοση που ενεργοποιούμε για unattended entries. Μην αλλάξεις ακόμη το running bot
χωρίς να το σταματήσεις. Το `New entries paused` δεν σταματά υπάρχοντα exit logic.

## 1. Σταμάτησε μόνο τον παλιό paper trader

Από τον φάκελο του προηγούμενου project, με το υπάρχον δικό σου configuration:

```powershell
docker compose -p micro_trading_bot --env-file .env.local stop paper-trader
```

Δεν εκτελούμε `down -v`, δεν διαγράφουμε runtime state και δεν αγγίζουμε Dark Signal.
Επιβεβαίωσε στο Docker Desktop ότι ο συγκεκριμένος trader είναι stopped. Η NVDA θέση
σου παραμένει στον paper λογαριασμό· το stop container δεν κλείνει θέση.

## 2. Κράτησε backup και αποσυμπίεσε ξεχωριστά

Μην αντικαταστήσεις τον παλιό φάκελο. Το νέο project βρίσκεται κάτω από
`micro_trading_bot`. Το ZIP δεν περιέχει keys, runtime state, logs ή μοντέλα.
Αντέγραψε το δικό σου configuration ως **αρχείο** `.env.local` (όχι φάκελο)
μόνο στο τοπικό νέο project. Μην το ανεβάσεις σε GitHub ή σε άλλο ZIP.
Άλλαξε όσα credentials έχουν ήδη κοινοποιηθεί σε προηγούμενα αρχεία.

## 3. Εκκίνησε μόνο το dashboard

Από τον νέο φάκελο `micro_trading_bot`:

```powershell
Test-Path docker-compose.yml
Test-Path .env.local
python -m scripts.check_docker_config
docker compose -p micro_trading_bot --env-file .env.local config --quiet
docker compose -p micro_trading_bot --env-file .env.local up -d --build --no-deps dashboard
docker compose -p micro_trading_bot --env-file .env.local ps --all
```

Περιμένουμε dashboard running και paper-trader stopped. Μην τρέξεις το γενικό
`up -d` ούτε το Start-Orbit.ps1 τώρα: μπορούν να ξεκινήσουν και trader.
Το dashboard ανοίγει στο `http://localhost:8080` με τον προηγούμενο δικό σου password.
Με stopped trader είναι σωστό να εμφανίζει offline όταν παλιώσει το heartbeat.
Το resume είναι κλειδωμένο σε αυτό το checkpoint.

## 4. Offline tests και research

Σε ξεχωριστό virtual environment με project dependencies και pytest:

```powershell
python -m pytest tests_safe -q
python -m scripts.backtesting.offline_backtest C:\path\ohlcv.csv --output research_output
```

CSV: `timestamp,open,high,low,close,volume`, UTC timestamps της αρχής κάθε μπάρας,
ταξινομημένα, μοναδικά και με έγκυρα OHLCV. Το research command δεν κάνει broker/feed
request. Υποθέτει stock whole shares και fixed brackets· δεν είναι crypto exit simulator.
Τα costs είναι παραμετροποιήσιμες υποθέσεις στον BacktestPolicy, όχι πραγματικά fees.
Δεν φορτώνεται ML ή fundamental overlay για αυτό το canonical technical baseline.

Μην χρησιμοποιήσεις legacy backtest output για να διαφημίσεις Sharpe, win rate ή returns.
Δεν έχει ολοκληρωθεί ακόμη ο συνολικός research pipeline.
