"""Atomic, fail-closed instructions shared by dashboard and paper trader."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def control_path() -> Path:
    return Path(os.getenv("CONTROL_FILE", Path(__file__).resolve().parent / "control.json"))


def read_control(path: Path | None = None) -> dict:
    """Absent/corrupt controls pause entries; existing positions may still exit."""
    path = path or control_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or type(raw.get("paused")) is not bool:
            raise ValueError("Invalid control document")
        return {
            "paused": raw["paused"],
            "stop_requested": raw.get("stop_requested") is True,
            "updated_at": raw.get("updated_at"),
        }
    except (FileNotFoundError, OSError, ValueError, UnicodeError):
        return {"paused": True, "stop_requested": False, "updated_at": None}


def write_control(*, paused: bool, stop_requested: bool = False, path: Path | None = None) -> dict:
    if type(paused) is not bool:
        raise ValueError("paused must be boolean")
    if type(stop_requested) is not bool:
        raise ValueError("stop_requested must be boolean")
    path = path or control_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "paused": paused,
        "stop_requested": stop_requested,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".control-", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            os.chmod(temp_name, 0o600)
            json.dump(value, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return value


def request_stop(path: Path | None = None) -> dict:
    """Pause entries and ask the local paper loop to exit after its current safe step."""
    return write_control(paused=True, stop_requested=True, path=path)
