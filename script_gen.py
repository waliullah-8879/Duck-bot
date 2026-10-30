"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
import re

import requests

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

PROMPT = """You write scripts for a daily 45-60 second vertical Facebook video about birds.

Topic: {topic}

Rules:
- Discuss only the bird named in the topic: ducks, geese, doves, starlings, or forest birds.
- Do not include mammals, hunting, or unrelated bird species. Never invent facts or statistics.
- Write the title and 110-140 word narration in natural Pakistani Urdu using Urdu script, not Roman Urdu.
- Open with an engaging hook and use clear sentences suitable for spoken narration.
- Give 5 short stock-footage search terms in English, all specifically naming the bird in the topic.

Return ONLY JSON with keys:
title (max 80 chars), narration (string), search_terms (list of 5), hashtags (list of 6, no # sign)."""

URDU_BIRD_NAMES = {
    "Mallard duck": "مالارڈ بطخ",
    "Wood duck": "ووڈ بطخ",
    "Northern pintail": "شمالی پن ٹیل بطخ",
    "Green-winged teal": "سبز پروں والی ٹیل بطخ",
    "Northern shoveler": "چمچ دار بطخ",
    "Bufflehead": "بفِل ہیڈ بطخ",
    "Canada goose": "کینیڈا کا ہنس",
    "Snow goose": "برفانی ہنس",
    "Greylag goose": "سرمئی ہنس",
    "Brant goose": "برینٹ ہنس",
    "Mourning dove": "مارننگ ڈوو",
    "Rock dove": "راک ڈوو",
    "Eurasian collared dove": "یوریشین کالرڈ ڈوو",
    "White-winged dove": "سفید پروں والی ڈوو",
    "European starling": "یورپی اسٹارلنگ",
    "Great horned owl": "گریٹ ہارنڈ الو",
    "Barred owl": "بارڈ الو",
    "Pileated woodpecker": "پائلی ایٹڈ ووڈپیکر",
    "Northern cardinal": "شمالی کارڈینل",
    "American robin": "امریکی رابن",
    "Blue jay": "بلیو جے",
    "Black-capped chickadee": "بلیک کیپڈ چکڈی",
}


def _bird_search_terms(topic: str) -> list[str]:
    subject = topic.split(":", 1)[0].strip()
    return [subject, f"{subject} bird", f"{subject} flying", f"{subject} feeding", f"{subject} close up"]


def _fallback(topic: str) -> dict:
    name = topic.split(":")[0]
    narration = (
        f"کیا آپ {URDU_BIRD_NAMES.get(name, 'اس پرندے')} کے بارے میں یہ دلچسپ بات جانتے ہیں؟ "
        f"آج ہم {URDU_BIRD_NAMES.get(name, 'اس پرندے')} کو قریب سے جانیں گے۔ "
        "پرندوں کی چونچ، پروں، آواز اور رہنے کی جگہ انہیں پہچاننے میں مدد دیتی ہے۔ "
        "قدرتی ماحول میں خاموشی سے مشاہدہ کریں اور گھونسلوں سے مناسب فاصلہ رکھیں۔ "
        "صاف پانی، محفوظ درخت اور صحت مند مسکن پرندوں کی زندگی کے لیے اہم ہیں۔ "
        "ہر پرندے کا اپنا کردار ہے، اس لیے ان کے مسکن کا خیال رکھنا ہم سب کی ذمہ داری ہے۔ "
        "مزید پرندوں کی دلچسپ باتوں کے لیے ہمارے ساتھ رہیے۔"
    )
    return {
        "title": URDU_BIRD_NAMES.get(name, "پرندوں کی دنیا"),
        "narration": narration,
        "search_terms": _bird_search_terms(topic),
        "hashtags": ["پرندے", "بطخ", "ہنس", "فطرت", "پرندوں_کی_دنیا", "پرندوں_کا_مسکن"],
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
        if not re.search(r"[\u0600-\u06FF]", data["narration"]):
            raise ValueError("Claude returned narration without Urdu script.")
        data["search_terms"] = _bird_search_terms(topic)
        return data
    except Exception as e:  # network / parse problems should not kill the daily run
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
