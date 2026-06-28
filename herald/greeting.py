# herald/greeting.py
# Generates and delivers the boot greeting

import datetime
import psutil
from herald.voice import speak

def get_time_of_day() -> str:
    """Returns greeting based on current hour"""
    hour = datetime.datetime.now().hour

    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Good night"

def get_system_status() -> dict:
    """
    Pulls current system health metrics
    psutil is a cross-platform library for system info
    """
    return {
        "cpu": psutil.cpu_percent(interval=1),
        "ram": psutil.virtual_memory().percent,
        "ram_available": round(psutil.virtual_memory().available / (1024**3), 1)
    }

def get_threats_blocked() -> int:
    """
    Reads overnight threat count from ALPHATRON logs
    Returns 0 for now — SENTINEL will populate this later
    """
    log_path = "/home/paachu/alphatron/logs/threats.log"
    try:
        with open(log_path, "r") as f:
            return len(f.readlines())
    except FileNotFoundError:
        return 0

def greet():
    """
    Builds and delivers the full boot greeting
    This is what gets called on system startup
    """
    time_greeting = get_time_of_day()
    status = get_system_status()
    threats = get_threats_blocked()

    # Build the greeting message
    message = f"{time_greeting}, Paachu. ALPHATRON is online. "
    message += f"System status — CPU at {status['cpu']} percent. "
    message += f"RAM at {status['ram']} percent, "
    message += f"{status['ram_available']} gigabytes available. "

    if threats == 0:
        message += "No threats detected overnight. All systems nominal."
    elif threats == 1:
        message += "1 threat was detected and neutralized overnight."
    else:
        message += f"{threats} threats were detected and neutralized overnight."

    # Speak it
    print(f"[ALPHATRON HERALD] {message}")
    speak(message)

if __name__ == "__main__":
    greet()
