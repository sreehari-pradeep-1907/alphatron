# optik/auth_watcher.py
# Taps into journalctl live and parses raw auth log lines
# into clean structured events for the classifier.

import subprocess
import re
from datetime import datetime

# Regex patterns to extract data from raw journalctl lines
# We match the EXACT phrases sshd/sudo write to the journal

SSH_FAILED_PATTERN = re.compile(
    r"Failed password for (?:invalid user )?(\S+) from (\S+) port (\d+)"
)
SSH_ACCEPTED_PATTERN = re.compile(
    r"Accepted password for (\S+) from (\S+) port (\d+)"
)
SUDO_FAILED_PATTERN = re.compile(
    r"authentication failure;.*?user=(\S+)"
)
SUDO_SUCCESS_PATTERN = re.compile(
    r"(\S+) : TTY=(\S+) ; PWD=(\S+) ; USER=(\S+) ; COMMAND=(.+)"
)


def _parse_line(line: str) -> dict | None:
    """
    Takes one raw journalctl line, tries every pattern,
    returns a structured event dict if it matches something
    we care about. Returns None if the line is irrelevant.
    """
    timestamp = datetime.now().isoformat()

    match = SSH_FAILED_PATTERN.search(line)
    if match:
        user, ip, port = match.groups()
        return {
            "type": "ssh_failed",
            "user": user,
            "ip": ip,
            "timestamp": timestamp,
        }

    match = SSH_ACCEPTED_PATTERN.search(line)
    if match:
        user, ip, port = match.groups()
        return {
            "type": "ssh_success",
            "user": user,
            "ip": ip,
            "timestamp": timestamp,
        }

    match = SUDO_FAILED_PATTERN.search(line)
    if match:
        user = match.group(1)
        return {
            "type": "sudo_failed",
            "user": user,
            "ip": "local",
            "timestamp": timestamp,
        }

    match = SUDO_SUCCESS_PATTERN.search(line)
    if match:
        user, tty, pwd, run_as, command = match.groups()
        return {
            "type": "sudo_success",
            "user": user,
            "ip": "local",
            "command": command,
            "timestamp": timestamp,
        }

    # Line didn't match anything we care about
    return None


def stream():
    """
    Generator — yields structured events one at a time,
    forever, as they happen live on the system.

    Uses journalctl -f to tail both sshd and sudo events
    in a single combined stream.
    """
    cmd = [
        "journalctl",
        "-f",
        "-n", "0",
        "_COMM=sudo",
        "+",
        "_SYSTEMD_UNIT=sshd.service",
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,  # line-buffered
    )

    for raw_line in process.stdout:
        event = _parse_line(raw_line)
        if event:
            yield event


if __name__ == "__main__":
    # Quick manual test — run this file directly to see live events
    print("[OPTIK] Watching auth events... (Ctrl+C to stop)")
    for event in stream():
        print(f"[EVENT] {event}")
