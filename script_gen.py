"""Turn a topic into a short-video script (narration + title + stock-footage search terms)."""
import json
import os
import re

import requests

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

PROMPT = """You write a 4-6 minute Urdu wildlife documentary for a vertical Facebook video.

Topic: {topic}

Rules:
- Focus the entire documentary on the one bird species named in the topic. Do not introduce other species.
- Write 550-700 words of narration in natural Pakistani Urdu using Urdu script, not Roman Urdu.
- Structure it as a documentary: opening, identification, habitat, feeding, behavior, seasonal life, and conservation.
- Use clear, unhurried sentences for voice narration. Be informative without padding or repeating points.
- Never invent facts, statistics, or conservation status. Qualify details that vary by region.
- Give 5 English stock-footage search terms, all naming only the selected species and different actions or views.

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


def _fallback(topic: str) -> dict:
    name = topic.split(":")[0]
    bird = URDU_BIRD_NAMES.get(name, "اس پرندے")
    narration = (
        f"آج کی اس دستاویزی ویڈیو میں ہم {bird} کی دنیا کا سفر کریں گے۔ کسی پرندے کو سمجھنے کے لیے صرف اس کے رنگ دیکھنا کافی نہیں؛ اس کی جسامت، چونچ، پروں کی بناوٹ، آواز، حرکت اور رہنے کی جگہ کو بھی غور سے دیکھنا پڑتا ہے۔ یہی نشانیاں ہمیں اس نوع کو پہچاننے اور اس کے ماحول کے ساتھ تعلق کو سمجھنے میں مدد دیتی ہیں۔\n\n"
        f"{bird} کو دیکھتے وقت پہلے اس کی مجموعی شکل پر توجہ دیں۔ سر اور جسم کا تناسب، گردن کی لمبائی، دم کی صورت، پروں پر موجود رنگ اور پرواز کا انداز اہم اشارے ہو سکتے ہیں۔ روشنی اور موسم کے ساتھ رنگ مختلف دکھائی دے سکتے ہیں، اس لیے صرف ایک نشان پر فیصلہ نہ کریں۔ کئی خصوصیات کو ایک ساتھ دیکھنا زیادہ قابلِ اعتماد طریقہ ہے۔\n\n"
        f"پرندوں کے پر صرف خوب صورتی کے لیے نہیں ہوتے۔ وہ جسم کو موسم سے بچاتے، پرواز میں مدد دیتے اور بعض اوقات دوسرے پرندوں کو اشارے بھی دیتے ہیں۔ پرندے اپنے پروں کی صفائی اور ترتیب پر وقت صرف کرتے ہیں۔ اس قدرتی نگہداشت سے پرواز اور جسمانی حفاظت میں مدد ملتی ہے۔ {bird} کے پروں کو قریب سے دیکھنے کے لیے دوربین یا اچھے کیمرے کا استعمال کریں، اسے پکڑنے یا گھونسلے کے قریب جانے کی ضرورت نہیں۔\n\n"
        f"ہر پرندہ اپنے ماحول سے خوراک اور پناہ حاصل کرتا ہے۔ چونچ کی بناوٹ، پاؤں کی ساخت اور جسم کا انداز اس بات کے بارے میں اشارہ دے سکتے ہیں کہ وہ کیسے کھاتا یا حرکت کرتا ہے۔ مختلف علاقوں میں ایک ہی نوع کی خوراک بھی بدل سکتی ہے۔ اسی لیے {bird} کے بارے میں مشاہدہ کرتے ہوئے اس جگہ، موسم اور دستیاب خوراک کو ذہن میں رکھنا ضروری ہے۔\n\n"
        f"قدرتی مسکن پرندے کی روزمرہ زندگی کی بنیاد ہے۔ درخت، جھاڑیاں، کھلے میدان، جھیلیں یا کنارے ہر جگہ مختلف سہولتیں فراہم کرتے ہیں۔ محفوظ جگہ اسے آرام، خوراک تلاش کرنے اور اپنے بچوں کی پرورش کا موقع دیتی ہے۔ مسکن میں تبدیلی آنے سے پرندوں کی نقل و حرکت اور خوراک کی دستیابی بھی متاثر ہو سکتی ہے۔ {bird} کو سمجھنے کے لیے اس کے ماحول کو بھی دیکھنا اتنا ہی ضروری ہے جتنا خود پرندے کو۔\n\n"
        f"آوازیں پرندوں کی زندگی کا ایک اہم حصہ ہیں۔ پکار کے ذریعے وہ ایک دوسرے سے رابطہ کرتے، خطرے سے خبردار کرتے یا اپنے علاقے کا اظہار کرتے ہیں۔ ہر آواز کا مطلب ہمیشہ ایک جیسا نہیں ہوتا؛ وقت، موسم اور اردگرد کی صورتحال بھی اہم ہوتی ہے۔ خاموشی سے سننا اور آواز کے ساتھ پرندے کی حرکت دیکھنا ہمیں بہتر انداز میں مشاہدہ کرنے میں مدد دیتا ہے۔\n\n"
        f"موسم بدلنے کے ساتھ خوراک، درجۂ حرارت اور دن کی لمبائی بھی بدلتی ہے۔ کئی پرندے ان تبدیلیوں کے مطابق اپنی سرگرمیوں کا وقت بدلتے ہیں، جبکہ بعض علاقوں میں ان کی آمد و رفت بھی موسم سے جڑی ہوتی ہے۔ ہر آبادی کا انداز ایک جیسا نہیں ہوتا، اس لیے کسی خاص علاقے کے مشاہدات کو پوری نوع پر لاگو نہیں کرنا چاہیے۔ مقامی معلومات اور کئی دنوں کا مشاہدہ زیادہ مکمل تصویر پیش کرتا ہے۔\n\n"
        f"پرندے قدرتی نظام میں اپنا کردار ادا کرتے ہیں۔ وہ خوراکی سلسلوں کا حصہ ہیں اور بعض انواع بیج پھیلانے یا کیڑوں کی تعداد کو متوازن رکھنے میں مدد دیتی ہیں۔ یہ کردار علاقے اور نوع کے مطابق مختلف ہو سکتا ہے۔ {bird} کی موجودگی ہمیں اس ماحول کے بارے میں بھی کچھ بتا سکتی ہے جس میں وہ رہتا ہے۔ صحت مند مسکن صرف ایک پرندے نہیں بلکہ بہت سی زندگیوں کو سہارا دیتا ہے۔\n\n"
        f"اس پرندے کا مشاہدہ کرتے وقت فاصلہ رکھیں، اچانک حرکت اور شور سے بچیں، اور گھونسلوں یا بچوں کو نہ چھوئیں۔ جنگلی پرندوں کو خوراک دینا بھی مناسب نہیں، کیونکہ اس سے ان کے قدرتی رویے متاثر ہو سکتے ہیں۔ صاف پانی، محفوظ سبز جگہیں اور ذمہ دارانہ رویہ پرندوں کے لیے بہتر ماحول بنانے میں مدد دیتے ہیں۔\n\n"
        f"{bird} کی زندگی کو سمجھنے کے لیے صبر سے دیکھنا، سننا اور درست معلومات پر بھروسا کرنا ضروری ہے۔ اگلی بار جب یہ پرندہ آپ کو نظر آئے تو اس کے رنگ کے ساتھ اس کی آواز، حرکت اور مسکن پر بھی غور کریں۔ قدرت کو اس کے اپنے انداز میں دیکھنا ہی ایک اچھے مشاہدے کی ابتدا ہے۔"
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
                "max_tokens": 3000,
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
        if len(data["narration"].split()) < 500:
            raise ValueError("Claude returned a narration that is too short for a documentary.")
        data["search_terms"] = _bird_search_terms(topic)
        return data
    except Exception as e:  # network / parse problems should not kill the daily run
        print(f"[script] Claude call failed ({e}); using fallback template.")
        return _fallback(topic)
