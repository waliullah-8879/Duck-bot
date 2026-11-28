"""Free high-clarity text-to-speech with edge-tts and multi-voice fallback."""
import asyncio
import os
from pathlib import Path
import re

import edge_tts

DEFAULT_VOICE = os.getenv("TTS_VOICE", "ur-IN-SalmanNeural")
CANDIDATE_VOICES = [
    DEFAULT_VOICE,
    "ur-IN-SalmanNeural",
    "ur-PK-AsadNeural",
    "ur-IN-GulNeural",
]
# Remove duplicates preserving order
CANDIDATE_VOICES = list(dict.fromkeys(CANDIDATE_VOICES))
RATE = os.getenv("TTS_RATE", "+4%")


def _clean_text_for_tts(text: str) -> str:
    """Normalize text to prevent TTS synthesis hiccups."""
    # Replace long dashes, bullets, and unusual brackets with clean separators
    cleaned = re.sub(r"[—–―]", "، ", text)
    cleaned = re.sub(r"[\*#_~`]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


async def _speak(text: str, out: str):
    cleaned = _clean_text_for_tts(text)
    out_path = Path(out)
    last_exc = None

    for voice in CANDIDATE_VOICES:
        try:
            print(f"[tts] Synthesizing voiceover with {voice} at {RATE} rate...")
            await edge_tts.Communicate(cleaned, voice, rate=RATE).save(str(out_path))
            if out_path.exists() and out_path.stat().st_size > 1024:
                print(f"[tts] Voiceover synthesis successful ({out_path.stat().st_size} bytes).")
                return
        except Exception as exc:
            print(f"[tts] Voice {voice} failed ({exc}); trying fallback voice...")
            last_exc = exc
            out_path.unlink(missing_ok=True)

    if last_exc:
        raise last_exc


def synthesize(text: str, out_path: str) -> str:
    asyncio.run(_speak(text, out_path))
    return out_path
