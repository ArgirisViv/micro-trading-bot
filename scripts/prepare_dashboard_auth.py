"""Generate local dashboard login settings without storing the password."""

from getpass import getpass
from secrets import token_urlsafe

from werkzeug.security import generate_password_hash


def main() -> None:
    password = getpass("Choose a dashboard password (12+ characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    if getpass("Confirm dashboard password: ") != password:
        raise SystemExit("Passwords did not match")
    print("Add these lines to .env.local (never commit that file):")
    print("DASHBOARD_PASSWORD_HASH=" + generate_password_hash(password))
    print("DASHBOARD_SESSION_SECRET=" + token_urlsafe(48))


if __name__ == "__main__":
    main()
