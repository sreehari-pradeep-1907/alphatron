# optik/optik.py
# The orchestrator — ties auth_watcher, classifier, and HERALD
# together into one live, continuous monitoring pipeline.

import os
from datetime import datetime

from optik import auth_watcher
from optik import classifier
from herald.voice import speak

LOG_FILE = os.path.join(os.path.dirname(__file__), "optik.log")


def _log(verdict: dict):
    """
    Writes every verdict to optik.log, regardless of severity.
    This is the audit trail — nothing is ever silently dropped,
    even INFO-level events get recorded for later review.
    """
    line = (
        f"{datetime.now().isoformat()} "
        f"[{verdict['severity']}] {verdict['reason']}\n"
    )
    with open(LOG_FILE, "a") as f:
        f.write(line)


def run():
    """
    Main loop — runs forever, watching live auth events,
    classifying each one, logging everything, and speaking
    only when the classifier says speak=True.
    """
    print("[OPTIK] Monitoring started. Watching auth events live...")
    speak("OPTIK monitoring layer is now active.")

    for event in auth_watcher.stream():
        verdict = classifier.classify(event)

        # Always log, regardless of severity — full audit trail
        _log(verdict)
        print(f"[{verdict['severity']}] {verdict['reason']}")

        # Only interrupt the user audibly for meaningful severity
        if verdict["speak"]:
            alert_message = f"Security alert. {verdict['reason']}"
            speak(alert_message)


if __name__ == "__main__":
    run()
