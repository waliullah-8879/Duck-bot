"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
import re

import requests

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

PROMPT = """You write scripts for a daily 45-60 second vertical Facebook video about ducks, \
waterfowl, lawful/ethical hunting and wildlife.

Topic: {topic}

Rules:
- Factual, engaging, educational. Never invent statistics; stay general if unsure.
- Hunting content must promote safety, legality, fair chase and conservation. No graphic gore, \
no encouragement of poaching or breaking regulations. Say regulations vary by region.
- Open with a hook in the first sentence. 110-140 words of narration, plain spoken sentences.
- Give 5 stock-footage search terms (2-3 words each) that match what is said, e.g. "mallard duck swimming".

Return ONLY JSON with keys:
title (max 80 chars), narration (string), search_terms (list of 5), hashtags (list of 6, no # sign)."""


def _fallback(topic: str) -> dict:
    name = topic.split(":")[0]
    narration = (
        f"Today's wildlife spotlight: {topic}. "
        f"{name} is one of the many fascinating stories in the outdoors. "
        "Wetlands, forests and open country support a huge variety of animals, "
        "and understanding them helps us protect the places they live. "
        "Whether you watch wildlife, photograph it, or take part in regulated hunting, "
        "respect for the animal and the law always comes first. "
        "Follow the page for a new wildlife story every single day."
    )
    return {
        "title": name[:80],
        "narration": narration,
        "search_terms": [name, "wildlife nature", "wetland birds", "forest wildlife", "lake sunrise"],
        "hashtags": ["wildlife", "ducks", "nature", "outdoors", "waterfowl", "conservation"],
    }


def generate_script(topic: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("[script] No ANTHROPIC_API_KEY set, using fallback template.")
        return _fallback(topic)
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 900,
                "messages": [{"role": "user", "content": PROMPT.format(topic=topic)}],
            },
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
        data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        for k in ("title", "narration", "search_terms", "hashtags"):
            assert k in data
        return data
    except Exception as e:  # network / parse problems should not kill the daily run
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
