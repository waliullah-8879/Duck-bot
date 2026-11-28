"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
from pathlib import Path
import random
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

PROMPT = """You write a viral, high-retention 30-40 second Urdu wildlife Reel for Facebook about a migratory bird species visiting Pakistan along the Indus Flyway.

Topic: {topic}

Rules:
- Focus entirely on the single migratory bird species named in the topic.
- Write 60-90 words of natural, exciting Pakistani Urdu narration in Urdu script (not Roman Urdu).
- The very first sentence must be an electric curiosity hook (dramatic question, shocking fact, or vivid mystery) that stops someone scrolling within 2 seconds.
- Highlight 2 fascinating, specific facts: its speed/flight stamina, diving depth, plumage colors, or wintering in Pakistani wetlands (e.g. Chashma, Taunsa, Haleji, Keenjhar).
- END with an engaging comment prompt inviting viewers to comment, share their thoughts, or follow.
- Use confident, energetic spoken Urdu. Never sound like a monotone textbook.
- Give 5 English footage searches, all naming only this exact species and different natural behaviors.
- Provide 15 trending viral hashtags relevant to Facebook Reels, wildlife, and Pakistan nature.

Return ONLY JSON with keys:
title (max 80 chars, includes species name & emoji), narration (string), search_terms (list of 5), hashtags (list of 15, no # sign)."""

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

# 8 diverse, non-repeating storytelling templates to ensure scripts are never monotone or repetitive
VARIED_TEMPLATES = [
    # 1. Journey & Arrival
    (
        "سائبیریا اور وسطی ایشیا کی شدید برفباری کے بعد، {bird} ہزاروں میل کا طوفانی سفر طے کر کے پاکستان کے شفاف پانیوں پر اتر چکا ہے!\n\n"
        "اس کی غیر معمولی قوتِ پرواز اور {focus} فطرت کا ایسا عجوبہ ہے جو ہر دیکھنے والے کو مسحور کر دیتا ہے۔ انڈس فلائی وے پر اس خوبصورت مہمان کی موجودگی ہمارے ماحول کا فخر ہے۔\n\n"
        "کیا آپ نے اس خوبصورت پرندے کو کبھی دیکھا ہے؟ کمنٹس میں ضرور بتائیں!"
    ),
    # 2. Speed & Agility
    (
        "ہوا میں بجلی جیسی تیزی اور پانی کی لہروں پر تیرنے کا کمال انداز—یہ ہے {bird}!\n\n"
        "یہ شاندار پرندہ اپنی پھرتی اور {focus} کے باعث دنیا بھر میں مشہور ہے۔ پاکستان کے آبی ذخائر جیسے چشمہ بیراج اور ہالیجی جھیل پر اس کا رقص واقعی قابلِ دید ہوتا ہے۔\n\n"
        "قدرت کے اس حسین نظارے کو لائک کریں اور ایسی مزید ویڈیوز کے لیے فالو کریں!"
    ),
    # 3. Colors & Feathers
    (
        "فطرت کے تمام دلکش رنگ سمٹ کر {bird} کے پروں میں جلوہ گر ہیں!\n\n"
        "دور دراز خطوں سے ہجرت کر کے آنے والا یہ مہمان پرندہ اپنی نایاب خوبصورتی اور {focus} سے ہماری جھیلوں کی رونق کو چار چاند لگا دیتا ہے۔ صبح کے وقت پانی پر اس کا عکس دیکھ کر دل خوش ہو جاتا ہے۔\n\n"
        "اس نایاب پرندے کے لیے ایک کمنٹ ضرور کریں!"
    ),
    # 4. Wetlands & Conservation
    (
        "پاکستان کے دریا اور جھیلیں دنیا کے نایاب ترین پرندوں کی محفوظ پناہ گاہ ہیں، اور انہی میں سب سے خاص نام {bird} کا ہے۔\n\n"
        "سردیوں کے موسم میں اس کا سکون بھرا انداز اور {focus} ہر پرندوں کے شوقین کی توجہ کھینچ لیتا ہے۔ یہ معصوم پرندے ہمارے ماحول کی خوبصورتی اور علامت ہیں۔\n\n"
        "پرندوں کی قدرتی آواز اور خوبصورتی پسند آئی ہو تو شیئر ضرور کریں!"
    ),
    # 5. Winter Survival
    (
        "منفی چالیس ڈگری کی کڑاکے دار برفانی سردی کو شکست دے کر، {bird} ہر سال ہماری جھیلوں کا رخ کرتا ہے۔\n\n"
        "اس کا زندہ دل انداز اور {focus} ہمیں یہ سبق دیتا ہے کہ سفر اور امید کا نام ہی زندگی ہے۔ پانی میں اس کا تیرنا اور خوراک کی تلاش کا انداز واقعی حیرت انگیز ہے۔\n\n"
        "کیا آپ کو اس پرندے کے بارے میں یہ خاص بات معلوم تھی؟"
    ),
    # 6. Deep Water & Diving
    (
        "پانی کی سطح پر پرسکون تیرتا ہوا {bird} جب اچانک گہرے پانیوں میں اترتا ہے تو دیکھنے والے دنگ رہ جاتے ہیں!\n\n"
        "اس کی چوکنی آنکھیں اور {focus} اسے ایک ماہر تیراک بناتی ہیں۔ پاکستان کے موسم سرما میں اس کا مشاہدہ قدرت کے قریب ہونے کا سب سے بہترین تجربہ ہے۔\n\n"
        "آپ کا پسندیدہ پرندہ کون سا ہے؟ کمنٹس میں اپنی رائے کا اظہار کریں!"
    ),
    # 7. Flocks & Sky Formations
    (
        "نیلے آسمان پر پروں کی لہریں اور خوبصورت ترتیب میں پرواز کرتا ہوا {bird} موسم سرما کی سب سے دلکش تصویر ہے!\n\n"
        "اس کا باہمی اتحاد، اپنے ساتھیوں کی حفاظت اور {focus} واقعی بے مثال ہے۔ ہر سال اس کی آمد سے ہماری جھیلوں میں ایک نئی زندگی دوڑ جاتی ہے۔\n\n"
        "ایسی خوبصورت قدرتی ویڈیوز روزانہ دیکھنے کے لیے ہمارے پیج کو ضرور فالو کریں!"
    ),
    # 8. Mystery of the Wild
    (
        "بغیر کسی نقشے کے ہزاروں کلومیٹر کا فاصلہ طے کر کے ٹھیک اسی مقام پر پہنچنا—یہ ہے {bird} کا ناقابلِ فراموش کمال!\n\n"
        "اس کا پروقار انداز اور {focus} خالقِ کائنات کی عظیم کاریگری کا منہ بولتا ثبوت ہے۔ ٹھنڈے پانیوں پر اس کے خوشگوار لمحات دل کو بے پناہ سکون بخشتے ہیں۔\n\n"
        "اس خوبصورت تخلیق کے لیے سبحان اللہ ضرور لکھیں!"
    ),
]


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


VIRAL_BASE_TAGS = [
    "Reels",
    "ReelsFB",
    "ViralReels",
    "TrendingReels",
    "ReelsViral",
    "ExplorePage",
    "FYP",
    "ViralVideo",
    "PakistanWildlife",
    "IndusFlyway",
    "BirdWatching",
    "Wildlife",
    "NatureLovers",
    "WildBirds",
    "Waterfowl",
    "BeautifulPakistan",
]


def _fallback(topic: str) -> dict:
    name, _, focus = topic.partition(":")
    bird = _urdu_species_name(name.strip())
    focus = focus.strip().rstrip(".")
    # Pick randomly from the 8 diverse templates so no two days sound alike
    template = random.choice(VARIED_TEMPLATES)
    narration = template.format(bird=bird, focus=focus)

    return {
        "title": f"🦆 {bird} | پاکستان کا نایاب مہاجر پرندہ",
        "narration": narration,
        "search_terms": bird_search_terms(topic),
        "hashtags": VIRAL_BASE_TAGS,
    }


def generate_script(topic: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("[script] No ANTHROPIC_API_KEY set, using dynamic fallback template.")
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
        if not 50 <= word_count <= 140:
            raise ValueError(f"Claude returned narration ({word_count} words) outside target range.")
        data["search_terms"] = bird_search_terms(topic)
        # Ensure full 16+ viral hashtags are included
        combined_tags = list(dict.fromkeys(data.get("hashtags", []) + VIRAL_BASE_TAGS))
        data["hashtags"] = combined_tags[:18]
        return data
    except Exception as e:
        print(f"[script] Claude call failed ({e}); using dynamic fallback template.")
        return _fallback(topic)
