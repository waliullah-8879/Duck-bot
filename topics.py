"""Topic pool + simple no-repeat rotation."""
import json
import random
from pathlib import Path

HISTORY = Path(__file__).parent / "history.json"

TOPICS = {
    "ducks": [
        "Common Pochard: diving behavior and seasonal plumage",
        "Mallard Duck: identifying its changing seasonal plumage",
        "Green-winged Teal: feeding behavior in shallow wetlands",
        "Blue-winged Teal: migration and seasonal movement",
        "Eurasian Teal: field marks and wetland habitat",
        "Wood Duck: nesting and life in wooded wetlands",
        "Northern Pintail: migration and long-distance flight",
        "Gadwall: feeding behavior and subtle field marks",
        "Eurasian Wigeon: grazing and seasonal movement",
        "Northern Shoveler: how its bill helps it feed",
        "Pekin Duck: domestication, care, and breed characteristics",
        "Muscovy Duck: identifying its distinctive features",
        "Mandarin Duck: plumage, habitat, and courtship display",
        "Indian Runner Duck: upright posture and active behavior",
        "Khaki Campbell Duck: breed history and egg-laying traits",
        "Cayuga Duck: dark plumage and domestic breed history",
        "Rouen Duck: domestic breed history and identification",
        "Call Duck: the history of this small domestic breed",
        "Swedish Blue Duck: plumage and heritage breed history",
        "Aylesbury Duck: the history of this English domestic breed",
        "Crested Duck: the crest and responsible breed care",
        "Silver Appleyard Duck: plumage and domestic breed history",
        "Welsh Harlequin Duck: plumage and domestic breed history",
        "East Indie Duck: dark plumage and breed history",
        "American Black Duck: habitat and identification",
        "Canvasback: diving behavior and wetland habitat",
        "Redhead Duck: seasonal plumage and diving behavior",
        "Ring-necked Duck: field marks and diving behavior",
        "Common Eider: coastal habitat and down feathers",
        "Long-tailed Duck: seasonal plumage and diving behavior",
        "Bufflehead: diving behavior and compact size",
        "Common Goldeneye: diving behavior and nesting habitat",
        "Harlequin Duck: fast-flowing water habitat",
        "Ruddy Duck: courtship display and wetland habitat",
    ],
    "geese": [
        "Canada Goose: family groups and seasonal movement",
        "Greylag Goose: calls, behavior, and habitat",
        "Snow Goose: migration and seasonal plumage",
        "Ross's Goose: identification and migration",
        "Barnacle Goose: nesting habitat and migration",
        "Brant Goose: coastal habitat and seasonal movement",
        "Cackling Goose: identification and migration",
        "Greater White-fronted Goose: field marks and migration",
        "Pink-footed Goose: migration and winter habitat",
        "Bean Goose: identification and seasonal movement",
        "Emperor Goose: coastal habitat and plumage",
        "Swan Goose: identification and domestication",
        "Egyptian Goose: habitat and distinctive markings",
        "Chinese Goose: domestic breed history and care",
        "African Goose: domestic breed history and care",
        "Embden Goose: domestic breed characteristics and care",
        "Toulouse Goose: domestic breed history and care",
        "Pilgrim Goose: domestic breed history and characteristics",
        "Sebastopol Goose: curled feathers and breed care",
        "Pomeranian Goose: domestic breed history and care",
        "Roman Goose: domestic breed history and characteristics",
        "Steinbacher Goose: domestic breed history and care",
        "Shetland Goose: heritage breed history and care",
        "American Buff Goose: domestic breed history and care",
        "Kholmogory Goose: domestic breed history and characteristics",
    ],
    "doves": [
        "Mourning Dove: recognizing its call and seasonal behavior",
        "Eurasian Collared Dove: identification and urban habitat",
        "Spotted Dove: field marks and feeding behavior",
        "Diamond Dove: size, plumage, and habitat",
        "Ring-necked Dove: identifying its neck marking",
        "Rock Dove: adaptation to cities and varied habitats",
        "White-winged Dove: field marks and feeding behavior",
        "White-tipped Dove: forest habitat and identification",
        "Inca Dove: scale-like plumage and dry habitat",
        "Common Ground Dove: small size and ground-feeding behavior",
        "Zebra Dove: barred plumage and familiar call",
        "Laughing Dove: call, habitat, and behavior",
        "African Collared Dove: identification and habitat",
        "Red-eyed Dove: call and woodland habitat",
        "Namaqua Dove: desert habitat and distinctive shape",
        "European Turtle Dove: migration and conservation",
        "Oriental Turtle Dove: identification and seasonal movement",
        "Emerald Dove: forest habitat and green plumage",
        "Pink-necked Green Pigeon: fruit diet and forest habitat",
        "Nicobar Pigeon: plumage and island habitat",
        "Victoria Crowned Pigeon: size, crest, and forest habitat",
        "Wonga Pigeon: forest floor behavior and identification",
        "Bar-shouldered Dove: field marks and woodland habitat",
        "Brown Cuckoo-Dove: long tail and forest habitat",
    ],
}

ORDER = ["ducks"] * 5 + ["geese", "doves"]


def _species(topic: str) -> str:
    return topic.split(":", 1)[0].strip().casefold()


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
    used = {_species(t) for t in h["used"]}
    pool = [t for t in TOPICS[cat] if _species(t) not in used]
    if not pool:  # everything in this category used: reset it
        category_species = {_species(t) for t in TOPICS[cat]}
        h["used"] = [u for u in h["used"] if _species(u) not in category_species]
        pool = TOPICS[cat]
    return cat, random.choice(pool)


def mark_used(topic: str):
    h = _load()
    h["used"].append(topic)
    h["day"] += 1
    HISTORY.write_text(json.dumps(h, indent=2))
