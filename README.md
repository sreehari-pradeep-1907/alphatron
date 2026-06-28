# ALPHATRON

### AI-powered Host Intrusion Defense System for Linux

ALPHATRON is an autonomous, voice-enabled cybersecurity defense system built from scratch for Arch Linux. It watches your system in real time, classifies threats using SIEM-style logic, and speaks to you — greeting you on boot and alerting you the moment something suspicious happens.

Built by [Sreehari Pradeep (Paachu)](https://github.com/paachu) — offensive security researcher, CTF player, and bug bounty hunter.

---

## Why ALPHATRON

Most personal intrusion detection setups are either too simple (`fail2ban`-style static rules) or too complex to build and explain end-to-end. ALPHATRON is designed to be:

- **Fully understood** — every module was built and debugged from first principles, not copy-pasted
- **Voice-first** — it talks to you like a copilot, not just a silent logger
- **Intelligent, not noisy** — uses pattern and severity-based classification to avoid alert fatigue
- **Modular** — each component has a single responsibility and can be tested independently

---

## Architecture

```
alphatron/
├── herald/              # Voice interface — boot greeting, spoken alerts
│   ├── voice.py          # TTS engine (edge-tts + mpg123)
│   └── greeting.py       # Boot greeting logic (time, system status, threat summary)
│
├── optik/                # Real-time monitoring layer — "the eye"
│   ├── auth_watcher.py    # Live journalctl parser (SSH + sudo events)
│   ├── baseline.py        # Memory — known IPs, rolling time-window failure tracking
│   ├── classifier.py      # SIEM-style severity classifier (INFO/LOW/MEDIUM/HIGH)
│   ├── optik.py           # Orchestrator — wires watcher → classifier → log/voice
│   └── state/
│       └── trusted_ips.json
│
├── main.py
├── alphatron.conf
└── README.md
```

**Modules planned next:** CORTEX (AI reasoning layer for ambiguous threats), INTERCEPTOR (automated response engine), CHRONICLE (web dashboard).

---

## Module 1 — HERALD (Voice Interface)

HERALD is ALPHATRON's voice. It greets the user on every system boot with a time-aware message, live system status, and an overnight threat summary — all spoken aloud through a fully local text-to-speech pipeline.

### How it works

```
System boots
    ↓
systemd user service triggers HERALD
    ↓
greeting.py builds the message:
    - time of day (morning/afternoon/evening/night)
    - CPU and RAM status (via psutil)
    - overnight threat count (from OPTIK's logs)
    ↓
voice.py converts text → speech:
    - edge-tts synthesizes the audio (neural TTS, natural-sounding)
    - mpg123 plays it through the system speakers
```

### Design decisions

- **Two-file separation** — `voice.py` is a pure TTS wrapper with one job: take text, speak it. `greeting.py` handles message logic. This follows the single responsibility principle — any other module (like OPTIK) can call `speak()` directly without depending on greeting logic.
- **systemd user service, not system service** — audio servers (PipeWire/PulseAudio) run in the user session, not at the system level. A system-level service can't reliably access the user's audio session, so HERALD runs via `systemctl --user`.
- **Retry logic for audio playback** — at early boot, the audio backend isn't always immediately ready even after systemd reports the session active. This is a race condition. Fixed with a startup delay (`ExecStartPre=/bin/sleep`) plus retry logic inside `speak()` itself, so the system degrades gracefully instead of crashing.

### Real bugs hit and fixed

| Bug | Root cause | Fix |
|---|---|---|
| `pygame.mixer` not available | Python 3.14 build lacked SDL audio support | Replaced pygame with `mpg123` subprocess call |
| Service ran but no sound at boot | Audio device not ready yet — race condition | Added `ExecStartPre=sleep` + retry loop with backoff in `speak()` |
| Silent failure under systemd | Audio backend (`out123`) couldn't open device at early boot | Confirmed via `journalctl --user -u alphatron.service`, fixed with the retry layer above |

---

## Module 2 — OPTIK (Real-Time Monitoring Layer)

OPTIK is ALPHATRON's eye. It watches live authentication activity (SSH and sudo) on the system, classifies each event using SIEM-style severity logic, and only interrupts the user with a spoken alert when something genuinely warrants it.

### How it works — full pipeline

```
journalctl -f (live stream: sudo + sshd events)
        ↓
auth_watcher.py
    - regex-parses raw log lines into structured events
    - e.g. {"type": "ssh_failed", "user": "paachu", "ip": "203.0.113.45", ...}
        ↓
baseline.py
    - checks: is this IP known/trusted?
    - checks: how many failures from this IP in the last N seconds?
    - maintains a rolling in-memory event history (auto-pruned)
        ↓
classifier.py
    - applies severity rules:
        INFO   → normal activity from known source
        LOW    → isolated failure, likely a typo
        MEDIUM → success from an unrecognized source
        HIGH   → brute-force pattern (3+ failures within 60s)
        ↓
optik.py
    - logs every verdict to optik.log (full audit trail, nothing dropped)
    - calls HERALD's speak() only for MEDIUM/HIGH severity
```

### Design decisions

- **Why classify severity instead of binary alert/ignore** — mirrors real SIEM tools (Splunk, Wazuh). A flat "alert" bucket causes alert fatigue; tiered severity lets the system stay quiet for noise and loud for real signal.
- **Why a self-learning trust list instead of static rules** — the user's schedule and remote access patterns are irregular (works at all hours, SSHs in frequently). A static time-window or "flag all remote logins" rule would be useless. Instead, OPTIK tracks known sources and treats genuinely new patterns — not just unusual timing — as the signal worth flagging.
- **Why log everything but only speak sometimes** — the audit trail (`optik.log`) is the permanent record for later review (and will feed CHRONICLE's dashboard). Voice alerts are reserved for what actually deserves the user's attention.
- **Why a `Type=simple` + `Restart=always` systemd service** — unlike HERALD's one-shot boot greeting, OPTIK needs to run continuously, forever, and recover automatically if it ever crashes.

### Real bugs hit and fixed

| Bug | Root cause | Fix |
|---|---|---|
| `journalctl ... + -u sshd` failed: `"+" can only be used between terms` | Mixed a flag-based unit match (`-u`) with a field-based OR (`+`) | Switched to two consistent field matches: `_COMM=sudo + _SYSTEMD_UNIT=sshd.service` |
| `IndentationError` in `auth_watcher.py` | Inconsistent indentation from manual editing | Rewrote the `stream()` function cleanly with consistent 4-space indentation |
| `ModuleNotFoundError: No module named 'edge_tts'` | Ran the script with system Python instead of the project venv | Activated venv (`source venv/bin/activate.fish`) before running |
| No log/voice output when running as a systemd service | Misunderstanding, not a bug — `LOW` severity is deliberately silent by design (single failures = likely typos) | Confirmed working as intended by checking `optik.log` directly and triggering an actual 3-attempt brute-force pattern |

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3 | Best library ecosystem for security tooling, audio, and system monitoring |
| Voice synthesis | edge-tts | Free, neural (natural-sounding), works fully offline-adjacent |
| Audio playback | mpg123 | Lightweight, Linux-native, no GUI dependency |
| System metrics | psutil | Cross-platform CPU/RAM/process introspection |
| Log source | journalctl (systemd journal) | Structured, queryable, real-time streaming via `-f` |
| Process management | systemd (user services) | Auto-start, auto-restart, proper session/audio integration |

---

## Design principles applied throughout

- **Principle of least privilege** — ALPHATRON runs as a normal user, not root. Even if a module is compromised, the blast radius stays contained to the user's own permissions.
- **Single responsibility per module** — each file does exactly one job (parse, remember, decide, or speak), making the system testable and easy to reason about in isolation.
- **Graceful degradation over hard failure** — race conditions (audio not ready, journal not available) are handled with retries and delays, not left to crash the service.
- **Signal over noise** — every design choice in OPTIK (severity tiers, self-learning trust, time-windowed pattern detection) exists specifically to avoid alert fatigue, the single biggest failure mode of naive intrusion detection.

---

## Status

```
✅ HERALD   — voice interface, boot greeting, spoken alerts (complete)
✅ OPTIK    — real-time auth monitoring, SIEM-style classification (complete)
⬜ CORTEX   — AI reasoning layer for ambiguous threats (planned)
⬜ INTERCEPTOR — automated response engine, IP blocking (planned)
⬜ CHRONICLE — web dashboard for live threat visualization (planned)
```

---

## Running it

```bash
# Clone and set up
git clone https://github.com/paachu/alphatron.git
cd alphatron
python3 -m venv venv
source venv/bin/activate.fish   # or activate for bash/zsh
pip install -r requirements.txt

# Enable HERALD (boot greeting)
systemctl --user daemon-reload
systemctl --user enable --now alphatron.service

# Enable OPTIK (live monitoring)
systemctl --user enable --now optik.service
```

---

## Built on

Arch Linux (Kuboid OS) · Kerala, India 🇮🇳
