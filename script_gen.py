"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
import re

import requests

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

PROMPT = """You write a 2-3 minute Urdu documentary for a vertical Facebook video.

Topic: {topic}

Rules:
- Focus the entire documentary on the single species named in the topic. Do not mention other species.
- Write 260-340 words of natural Pakistani Urdu narration in Urdu script, not Roman Urdu.
- Make this episode distinct and specific to the topic angle; do not reuse a generic bird script.
- Cover identification, habitat, feeding, behavior, and the particular topic angle in a clear documentary structure.
- Use unhurried, clear spoken sentences. Never pad or repeat points.
- Never invent facts, statistics, or conservation status. Qualify facts that vary by region.
- Give 5 English footage searches, all naming only this exact species and different views or actions.

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
    return [subject, f"{subject} in habitat", f"{subject} flying", f"{subject} feeding", f"{subject} close up"]


def _urdu_species_name(name: str) -> str:
    for english_name, urdu_name in URDU_BIRD_NAMES.items():
        if english_name.casefold() == name.casefold():
            return urdu_name
    lowered = name.casefold()
    if "goose" in lowered:
        return f"{name} ہنس"
    if "dove" in lowered or "pigeon" in lowered:
        return f"{name} فاختہ"
    return f"{name} بطخ"


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
        "search_terms": _bird_search_terms(topic),
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
        data["search_terms"] = _bird_search_terms(topic)
        return data
    except Exception as e:  # network / parse problems should not kill the daily run
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
