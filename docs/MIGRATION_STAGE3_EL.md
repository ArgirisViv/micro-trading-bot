# Stage-3 migration — μόνο dashboard για τώρα

1. Από το προηγούμενο project folder, κράτησε τον trader stopped:

```powershell
docker compose -p micro_trading_bot --env-file .env.local stop paper-trader
```

Αν έχεις ενεργοποιήσει exit supervisor από άλλη τοπική/πειραματική έκδοση, χρειάζεται
και αυτός stop πριν από backup/migration. Αυτή η release δεν σου είχε ζητήσει να τον
ενεργοποιήσεις. Μην σταματάς προστασία πραγματικών θέσεων χωρίς broker review:
container stop δεν κλείνει θέσεις ούτε υποκαθιστά exit management.

2. Κράτησε backup του παλιού project/configuration και runtime. Μην διαγράψεις
named volume/state/DB (`down -v` απαγορεύεται για αυτή τη μετάβαση). Αποσυμπίεσε
το ZIP ξεχωριστά, μπες στον εσωτερικό `micro_trading_bot` και αντέγραψε το δικό σου
configuration τοπικά ως αρχείο `.env.local`. Μην το κοινοποιήσεις ή ανεβάσεις σε GitHub.

3. Έλεγξε και αναβάθμισε **μόνο** dashboard:

```powershell
Test-Path docker-compose.yml
Test-Path .env.local
python -m scripts.check_docker_config
docker compose -p micro_trading_bot --env-file .env.local config --quiet
docker compose -p micro_trading_bot --env-file .env.local up -d --build --no-deps dashboard
docker compose -p micro_trading_bot --env-file .env.local ps --all
```

Dashboard running, trader stopped, crypto supervisor absent/disabled.
`http://localhost:8080`, ο προηγούμενος δικός σου password. Stale/offline heartbeat
ή supervisor not initialized είναι αναμενόμενα με stopped processes.

Μην εκτελέσεις generic `up -d`, `Start-Orbit.ps1`, profile `crypto-exits` ή trader start.
`PAPER_ENTRIES_APPROVED` παραμένει false. Μην αλλάξεις supervisor environment τώρα.

Ο dashboard reader δεν κάνει schema migration. Αν υπάρχει v1 DB μπορεί να δείξει
ledger unavailable μέχρι την ελεγχόμενη writer migration. Δεν καθαρίζουμε το DB για
να φύγει το μήνυμα. Η πραγματική migration/activation θα γίνει ως ξεχωριστή δοκιμή,
με backup, account/order review και επιβεβαίωση της κατάστασης των θέσεων.

## Offline tests

Σε virtual environment με project dependencies και pytest:

```powershell
python -m pytest tests_safe -q
```

Δεν απαιτούν πραγματικά API keys και απαγορεύουν network connections.
Το ZIP περιέχει κώδικα/tests/docs, όχι credentials, database ή προσωπική trading activity.
