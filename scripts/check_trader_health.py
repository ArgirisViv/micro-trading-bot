"""Container liveness check for the paper-trading loop (not broker readiness)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def heartbeat_is_fresh(path: Path, max_age_seconds: int = 300) -> bool:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        timestamp = datetime.fromisoformat(state["last_heartbeat"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()
        return 0 <= age <= max_age_seconds
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


if __name__ == "__main__":
    state_path = Path(os.getenv("STATE_FILE", "/app/runtime/state.json"))
    raise SystemExit(0 if heartbeat_is_fresh(state_path) else 1)
