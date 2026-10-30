"""Free text-to-speech with edge-tts."""
import asyncio
import os

import edge_tts

VOICE = os.getenv("TTS_VOICE", "ur-PK-AsadNeural")


async def _speak(text: str, out: str):
    await edge_tts.Communicate(text, VOICE, rate="+0%").save(out)


def synthesize(text: str, out_path: str) -> str:
    asyncio.run(_speak(text, out_path))
    return out_path
