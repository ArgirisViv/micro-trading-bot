# Orbit Terminal / 01 — ολοκληρωμένη έκδοση UI

Βάση: το `micro_trading_bot.zip` που έστειλες. Διατηρήθηκαν όλα τα αρχικά
αρχεία κώδικα εκτός του HTML του dashboard. Προστέθηκε το `terminal.css`.
Δεν αλλάζουν APIs, trading logic, password authentication, entry policy,
Docker services ή runtime volumes.

## Εγκατάσταση χωρίς απώλεια ρυθμίσεων

1. Κράτησε backup του υπάρχοντος project και το `.env.local` τοπικά.
2. Αποσυμπίεσε το νέο ZIP σε προσωρινό φάκελο.
3. Αντέγραψε τα περιεχόμενα του νέου `micro_trading_bot` στον **ίδιο
   υπάρχοντα φάκελο project**. Αποδέξου την αντικατάσταση αρχείων κώδικα.
   Το ZIP δεν περιλαμβάνει `.env.local`, συνεπώς δεν το αντικαθιστά.
   Μην διαγράψεις τον υπάρχοντα φάκελο πριν από τη συγχώνευση.
4. Από τον υπάρχοντα φάκελο του project στο PowerShell:

```powershell
python -m scripts.check_docker_config
docker compose --env-file .env.local config --quiet
```

Προχώρησε μόνο εφόσον οι έλεγχοι περάσουν χωρίς προειδοποιήσεις.

```powershell
docker compose --env-file .env.local up -d --build --no-deps dashboard
docker compose --env-file .env.local ps
```

5. Στο dashboard πάτα Ctrl+F5 και συνδέσου με τον dashboard κωδικό σου.

Η στοχευμένη εκκίνηση αναδημιουργεί μόνο το dashboard. Δεν απαιτείται
επανεκκίνηση του paper-trader για την αλλαγή UI. Μην εκτελέσεις `down -v`:
θα αφαιρούσε τα runtime volumes. Η χρήση του ίδιου υπάρχοντος φακέλου
διατηρεί το όνομα Compose project και την πρόσβαση στο ίδιο runtime volume.

## Credentials

Το ZIP που ανέβασες περιείχε `.env.local`. Δεν διαβάστηκαν οι τιμές του,
δεν χρησιμοποιήθηκαν για σύνδεση και δεν περιλαμβάνονται στο παραδοτέο.
Συνιστάται αντικατάσταση των API keys και των dashboard secrets που
περιείχε, επειδή το αρχείο ανέβηκε εκτός του υπολογιστή σου. Δεν σημαίνει
ότι έχει διαπιστωθεί κατάχρηση. Κράτησε τα νέα secrets μόνο τοπικά και μην
τα ανεβάζεις σε GitHub ή επόμενα ZIP.

## Έλεγχοι

- Διατήρηση όλων των αρχικών DOM IDs και έλεγχος μοναδικότητας.
- Έλεγχος ισορροπίας HTML tags και JavaScript syntax.
- Σύγκριση αρχικού/τελικού πακέτου ώστε ο μη σχετικός κώδικας να μείνει ίδιος.
- Δεν προστέθηκαν πλασματικές συναλλαγές ή αποτελέσματα.
- Προστέθηκαν responsive και dark/light CSS κανόνες.
- Ο οπτικός έλεγχος σε browser και το backend pytest suite δεν εκτελέστηκαν:
  δεν ήταν διαθέσιμα browser executable και pytest στο περιβάλλον.
- Δεν εκκινήθηκε trader και δεν έγιναν κλήσεις στα δικά σου APIs.

Ο τελικός έλεγχος εμφάνισης, γραφημάτων και ελέγχων θα γίνει στο τοπικό
dashboard σου μετά την εγκατάσταση.
