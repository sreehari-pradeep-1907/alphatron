# optik/baseline.py
# Gives OPTIK memory — tracks known IPs and recent failure
# patterns so the classifier can tell "normal" from "suspicious".

import json
import os
from datetime import datetime, timedelta

STATE_DIR = os.path.join(os.path.dirname(__file__), "state")
TRUSTED_IPS_FILE = os.path.join(STATE_DIR, "trusted_ips.json")

# In-memory rolling history of recent events
# Format: list of dicts with 'ip', 'type', 'timestamp' (datetime object)
_recent_events = []

# How long we keep events in memory before they "expire"
# Anything older than this is irrelevant for pattern detection
HISTORY_WINDOW_SECONDS = 300  # 5 minutes


def _load_trusted_ips() -> list:
    """Reads the trusted IP list from disk."""
    try:
        with open(TRUSTED_IPS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_trusted_ips(ips: list):
    """Writes the trusted IP list back to disk."""
    with open(TRUSTED_IPS_FILE, "w") as f:
        json.dump(ips, f, indent=2)


def is_known_ip(ip: str) -> bool:
    """
    Checks if this IP has been marked trusted before.
    'local' (sudo events) is always considered known.
    """
    if ip == "local":
        return True
    trusted = _load_trusted_ips()
    return ip in trusted


def add_trusted_ip(ip: str):
    """
    Marks an IP as trusted — called when the user confirms
    'yes that was me' for a new source.
    """
    trusted = _load_trusted_ips()
    if ip not in trusted:
        trusted.append(ip)
        _save_trusted_ips(trusted)


def record_event(event: dict):
    """
    Adds an event to the in-memory rolling history,
    then prunes anything older than HISTORY_WINDOW_SECONDS.
    """
    event_copy = event.copy()
    event_copy["_recorded_at"] = datetime.now()
    _recent_events.append(event_copy)
    _prune_old_events()


def _prune_old_events():
    """
    Removes events older than our window.
    Keeps the in-memory list from growing forever.
    """
    cutoff = datetime.now() - timedelta(seconds=HISTORY_WINDOW_SECONDS)
    global _recent_events
    _recent_events = [
        e for e in _recent_events if e["_recorded_at"] >= cutoff
    ]


def recent_failures(ip: str, event_type: str, window_seconds: int = 60) -> int:
    """
    Counts how many failure events from this IP happened
    within the last `window_seconds`.

    Example: recent_failures("203.0.113.45", "ssh_failed", 60)
    → "how many ssh_failed events from this IP in the last 60s"
    """
    cutoff = datetime.now() - timedelta(seconds=window_seconds)
    count = 0
    for e in _recent_events:
        if (
            e.get("ip") == ip
            and e.get("type") == event_type
            and e["_recorded_at"] >= cutoff
        ):
            count += 1
    return count
