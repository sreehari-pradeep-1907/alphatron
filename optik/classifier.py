# optik/classifier.py
# The decision brain — takes a structured event + baseline context,
# returns a SIEM-style verdict with severity, not just ignore/alert.

from optik import baseline

# Severity levels, lowest to highest
INFO = "INFO"
LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

BRUTE_FORCE_THRESHOLD = 3   # failures
BRUTE_FORCE_WINDOW = 60     # seconds


def classify(event: dict) -> dict:
    """
    Takes a raw event from auth_watcher, applies baseline context,
    and returns a verdict dict:

    {
        "severity": "HIGH",
        "reason": "Brute force pattern detected",
        "speak": True,
        "event": {...original event...}
    }
    """
    ip = event.get("ip")
    event_type = event.get("type")

    # Record this event into history FIRST, so it counts
    # toward any brute-force pattern check below
    baseline.record_event(event)

    # Rule 3 — brute force check (applies to both ssh and sudo failures)
    if event_type in ("ssh_failed", "sudo_failed"):
        failure_count = baseline.recent_failures(
            ip, event_type, BRUTE_FORCE_WINDOW
        )
        if failure_count >= BRUTE_FORCE_THRESHOLD:
            return _verdict(
                HIGH,
                f"Brute force pattern — {failure_count} {event_type} "
                f"attempts from {ip} within {BRUTE_FORCE_WINDOW}s",
                speak=True,
                event=event,
            )

    # Rule 4 — single isolated failure, just log
    if event_type in ("ssh_failed", "sudo_failed"):
        return _verdict(
            LOW,
            f"Isolated {event_type} from {ip}, likely a typo",
            speak=False,
            event=event,
        )

    # Rule 1 & 2 — success events, check if source is known
    if event_type in ("ssh_success", "sudo_success"):
        if baseline.is_known_ip(ip):
            return _verdict(
                INFO,
                f"Normal {event_type} from known source {ip}",
                speak=False,
                event=event,
            )
        else:
            return _verdict(
                MEDIUM,
                f"New unrecognized source {ip} — confirm if this was you",
                speak=True,
                event=event,
            )

    # Rule 5 — fallback for anything unclassified
    return _verdict(
        INFO,
        "Unclassified event, logged for review",
        speak=False,
        event=event,
    )


def _verdict(severity: str, reason: str, speak: bool, event: dict) -> dict:
    """Builds a consistent verdict dict — single place that defines the shape."""
    return {
        "severity": severity,
        "reason": reason,
        "speak": speak,
        "event": event,
    }
