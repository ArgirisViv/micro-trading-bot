# Εγκατάσταση stage 4 χωρίς trading

Κρατήστε τον προηγούμενο φάκελο ως backup. Μη διαγράψετε Docker volumes ή execution DB.
Οι runtime λειτουργίες και το SQLite schema 2 δεν αλλάζουν σε αυτό το checkpoint.

Αντικαταστήστε τον κώδικα με το νέο αντίγραφο, όχι τα προσωπικά credentials.
Μεταφέρετε το υπάρχον `.env.local` ως **αρχείο**, όχι φάκελο, στον νέο project root.
Μη στείλετε το περιεχόμενό του σε screenshots ή στο GitHub.

Πριν από rebuild, σταματήστε μόνο τις trading υπηρεσίες του project `micro_trading_bot`
από τον προηγούμενο φάκελο:

```powershell
docker compose -p micro_trading_bot --env-file .env.local stop paper-trader crypto-exit-supervisor
```

Αν η προηγούμενη έκδοση δεν έχει supervisor service, σταματήστε μόνο `paper-trader`.
Μην πειράξετε το Dark Signal. Από τον νέο εσωτερικό φάκελο `micro_trading_bot`:

```powershell
Test-Path docker-compose.yml
Test-Path .env.local
python -m scripts.check_docker_config
docker compose -p micro_trading_bot --env-file .env.local config --quiet
docker compose -p micro_trading_bot --env-file .env.local up -d --build --no-deps dashboard
docker compose -p micro_trading_bot --env-file .env.local ps --all
```

Και τα δύο Test-Path πρέπει να είναι True. Διατηρήστε `PAPER_ENTRIES_APPROVED=false`.
Το dashboard είναι monitoring-only στο localhost:8080. Stopped trader ή
unavailable supervisor είναι αναμενόμενα· δεν δηλώνουν επιτυχές broker integration.

Δεν έγιναν Docker build ή πραγματικές API δοκιμές κατά την offline ανάπτυξη.
