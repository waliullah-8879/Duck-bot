"""Topic pool + simple no-repeat rotation."""
import json
import random
from pathlib import Path

HISTORY = Path(__file__).parent / "history.json"

TOPICS = {
    "duck_species": [
        "Mallard duck: how its plumage changes through the year",
        "Wood duck: nesting in tree cavities",
        "Northern pintail: a long-distance migratory duck",
        "Green-winged teal: a small dabbling duck",
        "Northern shoveler: how its broad bill helps it feed",
        "Bufflehead: a tiny duck built for diving",
    ],
    "geese": [
        "Canada goose: family groups and seasonal movement",
        "Snow goose: migration in large flocks",
        "Greylag goose: calls and social behavior",
        "Brant goose: a coastal migrant",
    ],
    "doves": [
        "Mourning dove: recognizing its soft call",
        "Rock dove: how pigeons adapt to city life",
        "Eurasian collared dove: identifying its neck marking",
        "White-winged dove: field marks and feeding habits",
    ],
    "starlings": [
        "European starling: how its plumage shifts with the seasons",
        "European starling: how flock murmurations move together",
        "European starling: its talent for copying sounds",
        "European starling: finding food in a changing landscape",
    ],
    "forest_birds": [
        "Great horned owl: listening and hunting after dark",
        "Barred owl: recognizing its distinctive call",
        "Pileated woodpecker: how it searches tree trunks for food",
        "Northern cardinal: bright plumage and clear song",
        "American robin: finding food on the forest floor",
        "Blue jay: calls, feathers, and forest life",
        "Black-capped chickadee: surviving cold forest winters",
    ],
}

ORDER = list(TOPICS)


def _load():
    if HISTORY.exists():
        return json.loads(HISTORY.read_text())
    return {"used": [], "day": 0}


def pick_topic(override: str | None = None):
    """Return (category, topic). Rotates categories, avoids repeats."""
    if override:
        return "custom", override
    h = _load()
    cat = ORDER[h["day"] % len(ORDER)]
    pool = [t for t in TOPICS[cat] if t not in h["used"]]
    if not pool:  # everything in this category used: reset it
        h["used"] = [u for u in h["used"] if u not in TOPICS[cat]]
        pool = TOPICS[cat]
    return cat, random.choice(pool)


def mark_used(topic: str):
    h = _load()
    h["used"].append(topic)
    h["day"] += 1
    HISTORY.write_text(json.dumps(h, indent=2))
