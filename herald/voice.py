# herald/voice.py
# Handles all voice output for ALPHATRON
# Uses edge-tts for synthesis, aplay for playback (Linux native)

import asyncio
import edge_tts
import tempfile
import os
import subprocess

VOICE = "en-US-GuyNeural"

async def _synthesize(text: str, output_path: str):
    """Convert text to audio file using edge-tts"""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)

def speak(text: str, max_retries: int = 3, retry_delay: float = 2.0):
    """
    Main function — call this from anywhere in ALPHATRON
    to make the system speak. Retries if audio device
    isn't ready yet (common at early boot).
    """
    import time

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_path = f.name

    try:
        asyncio.run(_synthesize(text, temp_path))

        for attempt in range(1, max_retries + 1):
            result = subprocess.run(
                ["mpg123", "-q", temp_path],
                capture_output=True
            )
            if result.returncode == 0:
                break  # success, stop retrying
            else:
                print(f"[HERALD] Audio device not ready (attempt {attempt}/{max_retries}), retrying...")
                time.sleep(retry_delay)
        else:
            print("[HERALD] Failed to play audio after all retries")

    finally:
        os.unlink(temp_path)
