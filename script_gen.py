"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
import re

import requests

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")
SPECIES_SEARCH_ALIASES = {
    # Ducks & Waterfowl
    "mallard": ["mallard duck", "Anas platyrhynchos", "wild mallard"],
    "northern pintail": ["pintail duck", "Anas acuta", "northern pintail duck"],
    "northern shoveler": ["shoveler duck", "Spatula clypeata", "northern shoveler"],
    "common teal": ["eurasian teal", "Anas crecca", "teal duck"],
    "eurasian wigeon": ["wigeon duck", "Mareca penelope", "eurasian wigeon"],
    "gadwall": ["gadwall duck", "Mareca strepera"],
    "common pochard": ["pochard duck", "Aythya ferina"],
    "red-crested pochard": ["red crested pochard", "Netta rufina"],
    "tufted duck": ["tufted duck bird", "Aythya fuligula"],
    "garganey": ["garganey duck", "Spatula querquedula"],
    "ruddy shelduck": ["ruddy shelduck duck", "Tadorna ferruginea", "brahminy duck"],
    "common shelduck": ["shelduck", "Tadorna tadorna", "common shelduck duck"],
    # Geese
    "bar-headed goose": ["bar-headed goose flock", "Anser indicus"],
    "greylag goose": ["greylag goose flock", "Anser anser"],
    "greater white-fronted goose": ["white-fronted goose", "Anser albifrons"],
    # Cranes & Bustards
    "common crane": ["eurasian crane", "Grus grus", "common crane flock"],
    "demoiselle crane": ["demoiselle crane flock", "Anthropoides virgo", "Grus virgo"],
    "houbara bustard": ["asian houbara", "Chlamydotis macqueenii", "bustard bird"],
    # Waterbirds
    "greater flamingo": ["greater flamingo flock", "Phoenicopterus roseus"],
    "lesser flamingo": ["lesser flamingo flock", "Phoeniconaias minor"],
    "great white pelican": ["white pelican", "Pelecanus onocrotalus"],
    "dalmatian pelican": ["dalmatian pelican bird", "Pelecanus crispus"],
    "eurasian spoonbill": ["spoonbill bird", "Platalea leucorodia"],
    "black stork": ["black stork bird", "Ciconia nigra"],
    "white stork": ["white stork bird", "Ciconia ciconia"],
    # Cormorants & Gulls
    "black-headed gull": ["black-headed gull bird", "Chroicocephalus ridibundus"],
    "brown-headed gull": ["brown-headed gull bird", "Chroicocephalus brunnicephalus"],
    "common cormorant": ["great cormorant", "Phalacrocorax carbo", "cormorant bird"],
    "great cormorant": ["great cormorant bird", "Phalacrocorax carbo", "cormorant diving"],
    # Shorebirds
    "eurasian curlew": ["curlew bird", "Numenius arquata"],
    "common snipe": ["snipe bird", "Gallinago gallinago"],
    "little stint": ["little stint bird", "Calidris minuta"],
    "green sandpiper": ["green sandpiper bird", "Tringa ochropus"],
    "wood sandpiper": ["wood sandpiper bird", "Tringa glareola"],
    "common greenshank": ["greenshank bird", "Tringa nebularia"],
    "black-tailed godwit": ["godwit bird", "Limosa limosa"],
    "kentish plover": ["kentish plover bird", "Charadrius alexandrinus"],
    # Passerines
    "yellow wagtail": ["yellow wagtail bird", "Motacilla flava"],
    "white wagtail": ["white wagtail bird", "Motacilla alba"],
    "barn swallow": ["barn swallow bird", "Hirundo rustica"],
    "sand martin": ["sand martin bird", "bank swallow", "Riparia riparia"],
    "bluethroat": ["bluethroat bird", "Luscinia svecica"],
    "common starling": ["european starling", "Sturnus vulgaris", "starling flock"],
    "common chiffchaff": ["chiffchaff bird", "Phylloscopus collybita"],
    # Raptors
    "osprey": ["osprey bird flight", "Pandion haliaetus", "osprey catching fish"],
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
    "Northern Pintail": "شمالی پن ٹیل (سیخ پر)",
    "Northern Shoveler": "شمالی شولر (چمچ دار بطخ)",
    "Common Teal": "عام ٹیل (چھوٹی مرغابی)",
    "Eurasian Wigeon": "یوریشین وجن (سرخ سر بطخ)",
    "Gadwall": "گیڈوال بطخ (بوجھر)",
    "Common Pochard": "عام پوچارڈ (لال سر)",
    "Red-crested Pochard": "لال چوٹی والا پوچارڈ",
    "Tufted Duck": "ٹفٹڈ بطخ (کلغی دار بطخ)",
    "Garganey": "گارگنی بطخ (چیتوا)",
    "Ruddy Shelduck": "سرخاب (چکوا)",
    "Common Shelduck": "عام شیلڈک (چیلوا)",
    # Geese
    "Bar-headed Goose": "پٹی دار سر والا ہنس (راج ہنس)",
    "Greylag Goose": "سرمئی ہنس (مگھ)",
    "Greater White-fronted Goose": "سفید ماتھے والا ہنس",
    # Cranes & Bustards
    "Common Crane": "عام کونج",
    "Demoiselle Crane": "کونج (چھوٹی کونج)",
    "Houbara Bustard": "تلور (ہوبرہ تلور)",
    # Waterbirds
    "Greater Flamingo": "بڑا فلیمنگو (راج ہنس)",
    "Lesser Flamingo": "چھوٹا فلیمنگو",
    "Great White Pelican": "بڑا سفید پیلیکن (ہوصیل)",
    "Dalmatian Pelican": "ڈالمیشین پیلیکن",
    "Eurasian Spoonbill": "چمچ چونچ (اسپون بل)",
    "Black Stork": "سیاہ لک لک",
    "White Stork": "سفید لک لک",
    # Cormorants & Gulls
    "Black-headed Gull": "سیاہ سر والا گل",
    "Brown-headed Gull": "بھورے سر والا گل",
    "Common Cormorant": "جل کوّا (کارمورنٹ)",
    "Great Cormorant": "بڑا جل کوّا (گریٹ کارمورنٹ)",
    # Shorebirds
    "Eurasian Curlew": "یوریشین کرلیو (بڑی گوگلی)",
    "Common Snipe": "چہا (کامن سنائپ)",
    "Little Stint": "لٹل اسٹنٹ",
    "Green Sandpiper": "سبز سینڈ پائپر",
    "Wood Sandpiper": "ووڈ سینڈ پائپر",
    "Common Greenshank": "کامن گرین شینک (تماچا)",
    "Black-tailed Godwit": "سیاہ دم والا گاڈوٹ",
    "Kentish Plover": "کینٹش پلوور",
    # Passerines
    "Yellow Wagtail": "پیلی ممولا (ویگ ٹیل)",
    "White Wagtail": "سفید ممولا (دھوبی چڑیا)",
    "Barn Swallow": "ابابیل (بارن سوالو)",
    "Sand Martin": "ریت ابابیل (سینڈ مارٹن)",
    "Bluethroat": "نیلا گل گلو (بلیوتھروٹ)",
    "Common Starling": "تلیر (کامن اسٹارلنگ)",
    "Common Chiffchaff": "کامن چف چیف",
    # Raptors
    "Osprey": "مچھی مار عقاب (اوسپرے)",
}


def bird_search_terms(topic: str) -> list[str]:
    subject = topic.split(":", 1)[0].strip()
    aliases = SPECIES_SEARCH_ALIASES.get(subject.casefold(), [])
    candidates = [subject, *aliases, f"{subject} bird", f"{subject} in habitat", f"{subject} feeding"]
    return list(dict.fromkeys(candidates))[:5]


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
    if "dove" in lowered or "pigeon" in lowered:
        return f"{name} فاختہ"
    if "duck" in lowered or "teal" in lowered or "pochard" in lowered or "wigeon" in lowered or "shelduck" in lowered:
        return f"{name} بطخ"
    return name


def _fallback(topic: str) -> dict:
    name, _, focus = topic.partition(":")
    bird = _urdu_species_name(name.strip())
    focus = focus.strip().rstrip(".")
    narration = (
        f"کیا آپ جانتے ہیں کہ {bird} ہزاروں کلومیٹر کا طوفانی سفر طے کر کے ہر سال پاکستان کے دریاؤں اور جھیلوں پر کیوں پہنچتا ہے؟\n\n"
        f"یہ خوبصورت مہاجر پرندہ موسم سرما میں سائبیریا اور وسطی ایشیا کی شدید برفباری سے بچنے کے لیے انڈس فلائی وے کے ذریعے پاکستان کا رخ کرتا ہے۔ {bird} اپنی تیز رفتار پرواز، نایاب رنگوں اور {focus} کی وجہ سے شکار اور فطرت کے شوقین افراد میں بے حد مشہور ہے۔\n\n"
        f"پانی میں اس کی چستی اور غوطہ زنی واقعی لاجواب ہے۔ کیا آپ نے کبھی اپنے قریبی آبی ذخیرے پر اس پرندے کو دیکھا ہے؟ کمنٹس میں ضرور بتائیں اور ایسی مزید ویڈیوز کے لیے فالو کریں!"
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
            "PakistanHunting",
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
    except Exception as e:  # network / parse problems should not kill the daily run
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
