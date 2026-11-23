"""Topic pool + simple no-repeat rotation for migratory birds and waterfowl."""
import json
from pathlib import Path
import random

HISTORY = Path(__file__).parent / "history.json"

TOPICS = {
    "ducks": [
        "Mallard: seasonal migration and wetland plumage",
        "Wood Duck: vibrant colors and forest wetland habitat",
        "Mandarin Duck: exotic plumage and courtship display",
        "Common Merganser: sharp serrated bill and expert diving",
        "Common Teal: rapid flight and shallow wetland feeding",
        "Tufted Duck: underwater foraging and distinctive crest",
    ],
    "geese_and_swans": [
        "Canada Goose: V-formation flight and wetland nesting",
        "Greylag Goose: flock leadership and wetland grazing",
        "Egyptian Goose: ancient wetland heritage and striking eye markings",
        "Black Swan: elegant swimming and red bill contrast",
        "Mute Swan: graceful glide and majestic wingspan",
    ],
    "waterbirds": [
        "Greater Flamingo: filter feeding in saline lagoons",
        "Great White Pelican: cooperative fishing and soaring flight",
        "Dalmatian Pelican: massive wingspan and freshwater lakes",
        "White Stork: long-distance thermals and wetland foraging",
        "Black Stork: solitary habits and quiet forest wetlands",
        "Grey Heron: patient stealth hunting along water edges",
        "Great Egret: pristine white plumage and lightning strike feeding",
        "Common Kingfisher: high-speed diving and iridescent feathers",
    ],
    "cormorants": [
        "Great Cormorant: expert underwater fishing and wing drying",
        "Common Cormorant: deep diving and coastal roosting",
    ],
    "passerines": [
        "Yellow Wagtail: tail pumping and grassland insect hunting",
        "White Wagtail: urban adaptability and energetic motion",
        "Barn Swallow: aerial insect hunting and long-distance journey",
        "Common Starling: synchronized murmurations and winter flocks",
    ],
}

ORDER = [
    "ducks", "geese_and_swans", "waterbirds", "ducks", "cormorants",
    "waterbirds", "passerines", "ducks", "geese_and_swans",
]


def _species(topic: str) -> str:
    return topic.split(":", 1)[0].strip().casefold()


def _load():
    if HISTORY.exists():
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    return {"used": [], "day": 0}


def pick_topic(override: str | None = None, exclude_species=(), category_offset: int = 0):
    """Return an unused topic, optionally excluding species unavailable this run."""
    if override:
        return "custom", override
    h = _load()
    used = {_species(t) for t in h["used"]}
    excluded = {_species(t) for t in exclude_species}

    for offset in range(len(ORDER)):
        cat = ORDER[(h["day"] + category_offset + offset) % len(ORDER)]
        available = [t for t in TOPICS[cat] if _species(t) not in excluded]
        pool = [t for t in available if _species(t) not in used]
        if pool:
            return cat, random.choice(pool)
        if available:
            available_species = {_species(t) for t in available}
            h["used"] = [t for t in h["used"] if _species(t) not in available_species]
            return cat, random.choice(available)

    raise RuntimeError("No untried species remain in the topic pool.")


def mark_used(topic: str, also_used=()):
    h = _load()
    used_species = {_species(item) for item in h["used"]}
    for item in (*also_used, topic):
        if _species(item) not in used_species:
            h["used"].append(item)
            used_species.add(_species(item))
    h["day"] += 1
    HISTORY.write_text(json.dumps(h, indent=2), encoding="utf-8")
