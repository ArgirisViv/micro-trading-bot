"""Offline preflight before creating auto-restarting paper containers."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAPER_ENDPOINT = "https://paper-api.alpaca.markets"


def check_config(path: Path) -> list[str]:
    if not path.is_file():
        return ["Create .env.local from .env.example before starting Compose."]
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"\'')
    errors = []
    required = ["DASHBOARD_PASSWORD_HASH", "DASHBOARD_SESSION_SECRET",
                "APCA_API_KEY_ID", "APCA_API_SECRET_KEY"]
    for name in required:
        if not values.get(name):
            errors.append(f"Set {name} in .env.local.")
    if values.get("DASHBOARD_SESSION_SECRET") and len(values["DASHBOARD_SESSION_SECRET"]) < 32:
        errors.append("DASHBOARD_SESSION_SECRET must be at least 32 characters.")
    for name in ("STOCK_TRADING_URL", "CRYPTO_TRADING_URL"):
        if values.get(name, "").rstrip("/") != PAPER_ENDPOINT:
            errors.append(f"{name} must use the Alpaca paper endpoint.")
    asset_classes = {item.strip().lower() for item in values.get("ASSET_CLASSES", "stocks,crypto").split(",")}
    if "stocks" in asset_classes and not values.get("POLYGON_API_KEY"):
        errors.append("Set POLYGON_API_KEY for stock market data.")
    if "crypto" in asset_classes and not values.get("CRYPTOCOMPARE_API_KEY"):
        errors.append("Set CRYPTOCOMPARE_API_KEY for crypto market data.")
    return errors


if __name__ == "__main__":
    problems = check_config(ROOT / ".env.local")
    for problem in problems:
        print(problem)
    if problems:
        raise SystemExit(1)
    print("Configuration preflight passed. No credential values were displayed.")
