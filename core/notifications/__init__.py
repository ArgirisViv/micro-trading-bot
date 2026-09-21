from .handlers import send_telegram, send_slack, send_sms

def notify(text: str) -> bool:
    """
    Ενιαίο notify: δοκιμάζει Telegram και Slack (και SMS αν θες),
    επιστρέφει True αν πέτυχε τουλάχιστον ένα κανάλι.
    """
    ok = False

    # Telegram
    try:
        if send_telegram(text):
            ok = True
    except Exception:
        pass

    # Slack
    try:
        if send_slack(text):
            ok = True
    except Exception:
        pass

    # Προαιρετικά SMS (αν θες)
    # try:
    #     if send_sms(text):
    #         ok = True
    # except Exception:
    #     pass

    return ok

__all__ = ["send_telegram", "send_slack", "send_sms", "notify"]



