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

PROMPT = """You write a 2-3 minute Urdu wildlife documentary for a vertical Facebook video about a migratory bird species.

Topic: {topic}

Rules:
- Focus the entire documentary on the single migratory bird species named in the topic. Do not mention other species.
- Write 260-340 words of natural Pakistani Urdu narration in Urdu script, not Roman Urdu.
- Make this episode distinct and specific to the bird's migration route (such as the Indus Flyway), identification, seasonal habitat, feeding, and behavior.
- Use unhurried, clear spoken sentences. Never pad or repeat points.
- Never invent facts, statistics, or conservation status. Qualify facts that vary by region.
- Give 5 English footage searches, all naming only this exact species and different views or actions.

Return ONLY JSON with keys:
title (max 80 chars), narration (string), search_terms (list of 5), hashtags (list of 6, no # sign)."""

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
        f"آج کی دستاویزی ویڈیو میں ہماری توجہ صرف {bird} پر ہے۔ اس قسط کا موضوع {focus} ہے۔ ہم اس کی شناخت، رہائش، خوراک اور رویوں کو دیکھیں گے۔ موسم اور علاقے کے ساتھ مشاہدات بدل سکتے ہیں، اس لیے ہر بات کو مقامی ماحول کے تناظر میں سمجھیں۔\n\n"
        f"{bird} کو پہچاننے کے لیے جسمانی ساخت، چونچ، گردن، دم، پروں کے رنگ اور حرکت پر غور کریں۔ روشنی یا موسم کے باعث رنگ مختلف دکھائی دے سکتے ہیں، اس لیے ایک نشان کے بجائے کئی خصوصیات کو ساتھ دیکھیں۔ مشاہدے کے لیے دوربین یا کیمرہ استعمال کریں، پرندے کو پکڑنے یا اس کے قریب جانے کی کوشش نہ کریں۔\n\n"
        f"اس کی رہائش روزمرہ زندگی کا اہم حصہ ہے۔ پانی، پودوں، درختوں، کھلی جگہ اور محفوظ گھونسلے کی دستیابی اثر ڈال سکتی ہے کہ {bird} کہاں آرام کرتا اور خوراک تلاش کرتا ہے۔ صرف پرندے کو نہیں، اس کے اردگرد کے مسکن کو بھی غور سے دیکھیں۔\n\n"
        f"خوراک حاصل کرنے کا انداز چونچ، پاؤں اور حرکت سے جڑا ہوتا ہے۔ دیکھیں کہ {bird} اپنے مسکن میں کس جگہ اور کس انداز سے خوراک تلاش کرتا ہے۔ موسم اور دستیاب خوراک اس کے رویے میں فرق ڈال سکتے ہیں؛ ایک مشاہدے کو ہر جگہ کی مستقل عادت نہ سمجھیں۔\n\n"
        f"آواز، پرواز، آرام اور دوسری حرکات کو مختلف اوقات میں دیکھنے سے اس کے رویے کو سمجھنے میں مدد ملتی ہے۔ موسم کے ساتھ سرگرمی یا نقل و حرکت بدل سکتی ہے، لیکن یہ فرق ہر علاقے میں یکساں نہیں ہوتا۔ صبر سے کیے گئے کئی مشاہدات زیادہ مکمل تصویر پیش کرتے ہیں۔\n\n"
        f"صاف اور محفوظ مسکن پرندے کے لیے اہم ہے۔ گھونسلوں سے فاصلہ رکھیں، شور نہ کریں اور جنگلی پرندوں کو نہ چھوئیں۔ {bird} کے بارے میں مزید جاننے کے لیے معتبر مقامی معلومات سے مدد لیں۔ اس قسط میں ہم نے صرف اسی نوع پر توجہ رکھی؛ اگلی بار خاموشی اور مناسب فاصلے سے اس کے قدرتی رویے دیکھیں۔"
    )
    return {
        "title": f"{bird} کے بارے میں",
        "narration": narration,
        "search_terms": bird_search_terms(topic),
        "hashtags": ["پرندے", "فطرت", "قدرتی_ماحول", "دستاویزی_فلم", "پرندوں_کا_مشاہدہ", "اردو"],
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
                "max_tokens": 2200,
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
        if not 240 <= word_count <= 380:
            raise ValueError("Claude returned narration outside the 2-3 minute length range.")
        data["search_terms"] = bird_search_terms(topic)
        return data
    except Exception as e:  # network / parse problems should not kill the daily run
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
