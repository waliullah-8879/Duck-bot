"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
from pathlib import Path
import re

import requests

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

SPECIES_SEARCH_ALIASES = {
    # Ducks & Waterfowl
    "mallard": ["mallard duck", "Anas platyrhynchos", "wild mallard", "mallard drake"],
    "wood duck": ["wood duck", "Aix sponsa", "wood duck swimming"],
    "mandarin duck": ["mandarin duck", "Aix galericulata", "mandarin duck swimming"],
    "common merganser": ["common merganser", "Mergus merganser", "goosander"],
    "common teal": ["eurasian teal", "Anas crecca", "teal duck"],
    "tufted duck": ["tufted duck", "Aythya fuligula", "tufted duck swimming"],
    # Geese & Swans
    "canada goose": ["canada goose", "Branta canadensis", "canada geese"],
    "greylag goose": ["greylag goose", "Anser anser", "greylag geese"],
    "egyptian goose": ["egyptian goose", "Alopochen aegyptiaca"],
    "black swan": ["black swan", "Cygnus atratus", "black swan swimming"],
    "mute swan": ["mute swan", "Cygnus olor", "white swan"],
    # Waterbirds & Waders
    "greater flamingo": ["greater flamingo", "Phoenicopterus roseus", "flamingo flock"],
    "great white pelican": ["white pelican", "Pelecanus onocrotalus", "great white pelican"],
    "dalmatian pelican": ["dalmatian pelican", "Pelecanus crispus"],
    "white stork": ["white stork", "Ciconia ciconia", "stork bird"],
    "black stork": ["black stork", "Ciconia nigra"],
    "grey heron": ["grey heron", "Ardea cinerea", "heron bird"],
    "great egret": ["great egret", "Ardea alba", "white egret"],
    "common kingfisher": ["kingfisher", "Alcedo atthis", "common kingfisher"],
    # Cormorants
    "common cormorant": ["great cormorant", "Phalacrocorax carbo", "cormorant bird"],
    "great cormorant": ["great cormorant", "Phalacrocorax carbo", "cormorant diving"],
    # Passerines
    "yellow wagtail": ["yellow wagtail", "Motacilla flava"],
    "white wagtail": ["white wagtail", "Motacilla alba"],
    "barn swallow": ["barn swallow", "Hirundo rustica"],
    "common starling": ["european starling", "Sturnus vulgaris", "starling flock"],
}

PROMPT = """You write a viral, high-retention 45-60 second Urdu wildlife Reel for Facebook about a migratory bird species visiting Pakistan along the Indus Flyway.

Topic: {topic}

Rules:
- Focus entirely on the single migratory bird species named in the topic.
- Write 85-125 words of natural, exciting Pakistani Urdu narration in Urdu script (not Roman Urdu).
- START with an irresistible 1-sentence curiosity hook that stops the scroll within 3 seconds (e.g. asking a surprising question about its incredible migration, flying speed, or survival in winter).
- Highlight 2-3 fascinating facts: where it migrates from (Siberia/Central Asia), its unique identification/plumage, and its behavior in Pakistani wetlands (e.g. Chashma, Taunsa, Haleji).
- END with an engaging question inviting viewers to comment and follow the page (e.g. asking if they have spotted this bird in their area).
- Use natural, energetic spoken Urdu sentences. Never sound like a dull textbook.
- Give 5 English footage searches, all naming only this exact species and different views or actions.

Return ONLY JSON with keys:
title (max 80 chars), narration (string), search_terms (list of 5), hashtags (list of 8, no # sign)."""

URDU_BIRD_NAMES = {
    # Ducks & Waterfowl
    "Mallard": "مالارڈ بطخ (نیل سر)",
    "Wood Duck": "ووڈ بطخ (رنگین بطخ)",
    "Mandarin Duck": "مینڈارن بطخ (شاہکار بطخ)",
    "Common Merganser": "کامن مرگانسر (ماہی خور بطخ)",
    "Common Teal": "عام ٹیل (چھوٹی مرغابی)",
    "Tufted Duck": "ٹفٹڈ بطخ (کلغی دار بطخ)",
    # Geese & Swans
    "Canada Goose": "کینیڈین ہنس (کینیڈا گوز)",
    "Greylag Goose": "سرمئی ہنس (مگھ)",
    "Egyptian Goose": "مصری ہنس (ایجپشین گوز)",
    "Black Swan": "کالا راج ہنس (بلیک سوان)",
    "Mute Swan": "سفید راج ہنس (میوٹ سوان)",
    # Waterbirds & Waders
    "Greater Flamingo": "بڑا فلیمنگو (راج ہنس)",
    "Great White Pelican": "بڑا سفید پیلیکن (ہوصیل)",
    "Dalmatian Pelican": "ڈالمیشین پیلیکن",
    "White Stork": "سفید لک لک",
    "Black Stork": "سیاہ لک لک",
    "Grey Heron": "سرمئی بگلا (گرے ہیرون)",
    "Great Egret": "بڑا سفید بگلا (گریٹ ایگریٹ)",
    "Common Kingfisher": "کنگ فشر (نیل کنٹھ مچھی مار)",
    # Cormorants
    "Common Cormorant": "جل کوّا (کارمورنٹ)",
    "Great Cormorant": "بڑا جل کوّا (گریٹ کارمورنٹ)",
    # Passerines
    "Yellow Wagtail": "پیلی ممولا (ویگ ٹیل)",
    "White Wagtail": "سفید ممولا (دھوبی چڑیا)",
    "Barn Swallow": "ابابیل (بارن سوالو)",
    "Common Starling": "تلیر (کامن اسٹارلنگ)",
}


def bird_search_terms(topic: str) -> list[str]:
    subject = topic.split(":", 1)[0].strip()
    aliases = SPECIES_SEARCH_ALIASES.get(subject.casefold(), [])
    candidates = [
        subject,
        *aliases,
        f"{subject} wildlife",
        f"{subject} swimming",
        f"{subject} flying",
        f"{subject} bird",
    ]
    return list(dict.fromkeys(candidates))[:6]


def _urdu_species_name(name: str) -> str:
    for english_name, urdu_name in URDU_BIRD_NAMES.items():
        if english_name.casefold() == name.casefold():
            return urdu_name
    lowered = name.casefold()
    if "goose" in lowered:
        return f"{name} ہنس"
    if "crane" in lowered:
        return f"{name} کونج"
    if "stork" in lowered:
        return f"{name} لک لک"
    if "gull" in lowered:
        return f"{name} گل"
    if "swan" in lowered:
        return f"{name} راج ہنس"
    if "duck" in lowered or "teal" in lowered or "pochard" in lowered or "wigeon" in lowered or "shelduck" in lowered or "merganser" in lowered:
        return f"{name} بطخ"
    return name


def _fallback(topic: str) -> dict:
    name, _, focus = topic.partition(":")
    bird = _urdu_species_name(name.strip())
    focus = focus.strip().rstrip(".")
    narration = (
        f"کیا آپ جانتے ہیں کہ {bird} ہر سال موسم سرما میں ہزاروں کلومیٹر کا طوفانی سفر طے کر کے پاکستان کی جھیلوں پر کیوں آتا ہے؟\n\n"
        f"سائبیریا اور وسطی ایشیا کی شدید سردی سے بچنے کے لیے یہ شاندار پرندہ انڈس فلائی وے کے ذریعے ہمارے آبی ذخائر کا رخ کرتا ہے۔ {bird} اپنی تیز رفتار پرواز، خوبصورت پروں اور {focus} کی بدولت دنیا بھر میں بے حد مقبول ہے۔\n\n"
        f"پانی میں اس کی تیراکی اور انداز واقعی دیکھنے سے تعلق رکھتا ہے۔ کیا آپ نے کبھی اس پرندے کو اپنے قریبی دریا یا جھیل پر دیکھا ہے؟ کمنٹس میں ضرور بتائیں اور پیج کو فالو کرنا نہ بھولیں!"
    )
    return {
        "title": f"{bird} | پاکستان کا نایاب مہاجر پرندہ",
        "narration": narration,
        "search_terms": bird_search_terms(topic),
        "hashtags": [
            "Reels",
            "ViralReels",
            "PakistanWildlife",
            "MigratoryBirds",
            "IndusFlyway",
            "Waterfowl",
            "BirdWatching",
            "NatureLovers",
        ],
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
                "max_tokens": 1200,
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
        word_count = len(data["narration"].split())
        if not 70 <= word_count <= 150:
            raise ValueError(f"Claude returned narration ({word_count} words) outside the 45-60 second Reel range.")
        data["search_terms"] = bird_search_terms(topic)
        return data
    except Exception as e:
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
