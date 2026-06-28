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

def speak(text: str):
    """
    Main function — call this from anywhere in ALPHATRON
    to make the system speak
    """
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_path = f.name

    try:
        # Generate the audio file
        asyncio.run(_synthesize(text, temp_path))

        # Use mpg123 to play mp3 — lightweight, Linux native
        subprocess.run(
            ["mpg123", "-q", temp_path],
            check=True
        )

    finally:
        os.unlink(temp_path)
