import os, requests, logging

def send_telegram(text: str) -> bool:
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    chat  = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat:
        logging.warning("Missing TELEGRAM_TOKEN/TELEGRAM_CHAT_ID")
        return False

    if len(text) > 4096:
        text = text[:4093] + "..."
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": int(chat), "text": text},
        timeout=15
    )
    r.raise_for_status()
    return True

def send_slack(text: str) -> bool:
    # placeholder (μην κάνουμε τίποτα προς το παρόν)
    return False

def send_sms(text: str) -> bool:
    # placeholder για να μην πέφτουμε σε Twilio errors
    return False
