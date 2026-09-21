# Λήψη πραγματικών ιστορικών δεδομένων — read-only

Αυτό είναι προσθήκη εργαλείου στο stage 4, **όχι** ολοκληρωμένη αξιολόγηση
απόδοσης ούτε ενεργοποίηση trading. Δεν έγινε πραγματική API λήψη κατά την ανάπτυξη.

## 1. Προετοιμασία

Αποσυμπιέστε το νέο ZIP σε νέο φάκελο και ανοίξτε τον εσωτερικό `micro_trading_bot`
στο VS Code. Κρατήστε το προηγούμενο αντίγραφο και τα runtime volumes.
Αντιγράψτε το δικό σας `.env.local` ως αρχείο στον νέο root. Δεν περιλαμβάνεται
στο ZIP. Το εργαλείο διαβάζει το `POLYGON_API_KEY`, χωρίς να το εκτυπώνει ή
να το βάζει στο CSV/metadata. Δεν εισάγει config ή broker SDK και δεν υποβάλλει orders.

Έλεγχος φακέλου:

```powershell
Test-Path .\scripts\download_research_data.py
Test-Path .env.local
```

Και τα δύο πρέπει να δώσουν True. Η λήψη δεν απαιτεί να ξεκινήσει κανένα container.
Για εκτέλεση απευθείας στα Windows χρειάζονται Python και οι dependencies.
Προτείνεται Python 3.12 ή 3.13 σε ξεχωριστό venv αντί του ήδη εγκατεστημένου 3.14:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pandas requests python-dotenv
```

Αν δεν έχετε Python 3.12, μην συνεχίσετε με εγκαταστάσεις στα τυφλά· στείλτε μόνο
το μήνυμα σφάλματος για να προσαρμόσουμε τις οδηγίες. Για όλο το research pipeline
χρειάζονται επίσης numpy, scikit-learn και joblib.

## 2. Πρώτη λήψη — AAPL, 5-minute bars

```powershell
.\.venv\Scripts\python.exe -m scripts.download_research_data --symbol AAPL --start 2025-10-01 --end 2026-09-14 --timeframe 5min --output .\research_data_AAPL_001
```

Οι ημερομηνίες είναι inclusive ημερολογιακές ημέρες Eastern Time. Δεκτές μόνο
ολοκληρωμένες ημέρες, μέχρι 365 calendar days ανά run. Υποστηρίζονται 1min, 5min,
15min, 30min, 1h — όχι stock daily bars με μη πιστοποιημένη session-close πολιτική.
Μέχρι 20 pages, 12 δευτερόλεπτα αναμονή ανά πρόσθετο page, timeout 5/20s, no retries.
Μπορεί να χρειαστούν αρκετά λεπτά· δεν υπάρχει απαίτηση να γίνει login στο dashboard.

Θα δημιουργηθεί νέος φάκελος με `bars.csv` και `dataset.json`. Υπάρχων output
φάκελος δεν αντικαθίσταται. Network/HTTP/pagination error σταματά ολόκληρη τη λήψη
πριν γραφτεί dataset. Τοπικό write error μπορεί να αφήσει ατελή output φάκελο:
μην τον θεωρήσετε επιτυχημένο και επιλέξτε νέο όνομα στο επόμενο run.

401/403 → KEY/plan access χρειάζεται έλεγχο. 429 → σταματήστε και περιμένετε.
**Μην αγοράσετε συνδρομή πριν εξετάσουμε το αποτέλεσμα.** Η ύπαρξη key δεν
αποδεικνύει ότι η ζητούμενη ιστορία/recency είναι διαθέσιμη στο δικό σας plan.

## 3. Τι να στείλετε

Αρχικά στείλτε μόνο το terminal αποτέλεσμα, όχι `.env.local`, keys ή ολόκληρο
project ZIP με credentials. Σε επιτυχία, μπορούμε να δουλέψουμε με `bars.csv`
και `dataset.json`, εφόσον οι όροι του δικού σας data plan επιτρέπουν αυτή τη χρήση.
Μη δημοσιεύσετε τα raw vendor δεδομένα στο GitHub ως default.

## Όρια

Offline verification: 236 tests στο πλήρες suite, με mocked HTTP pagination,
redaction errors, timezone/DST boundaries, CSV/metadata export, no-overwrite και
έλεγχο ότι ο exporter δεν εισάγει project config/broker modules.
Δεν χρησιμοποιήθηκαν πραγματικά credentials ούτε έγινε real API smoke test.

Όλες οι provider qualifying sessions διατηρούνται (pre/regular/post market).
Δεν γίνεται σιωπηρή αλλαγή session policy, gap filling ή ημερολογιακή πιστοποίηση.
Split-adjusted δεδομένα ζητούνται, όχι dividend-adjusted total returns.
Metadata περιλαμβάνει symbol, χρονικά όρια, αριθμό pages/rows και CSV SHA-256.
Μία επιτυχημένη λήψη δεν αποδεικνύει πληρότητα ιστορίας ή κερδοφορία.

Επίσημη τεκμηρίωση:
[Massive Custom Bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars).
Οι πίνακες plan access/recency/history και οι κανόνες aggregates πρέπει να
ελεγχθούν για τον δικό σας λογαριασμό. Δεν παρακάμπτουμε permissions ή billing.

Trader και supervisor παραμένουν stopped/disabled. Η παρούσα διαδικασία δεν
περιλαμβάνει `docker compose up`, αλλαγή approval flags ή πραγματικές συναλλαγές.
