"""Topic pool + simple no-repeat rotation for migratory birds."""
import json
from pathlib import Path
import random

HISTORY = Path(__file__).parent / "history.json"

TOPICS = {
    "ducks": [
        "Mallard: seasonal migration and wetland plumage",
        "Northern Pintail: long-distance flight and aerodynamic shape",
        "Northern Shoveler: specialized bill and surface feeding",
        "Common Teal: rapid flight and shallow wetland habitat",
        "Eurasian Wigeon: grazing habits and distinctive whistle call",
        "Gadwall: subtle plumage and dabbling behavior",
        "Common Pochard: diving behavior and winter flocking",
        "Red-crested Pochard: striking plumage and diving depth",
        "Tufted Duck: underwater foraging and distinctive crest",
        "Garganey: nocturnal migration and breeding plumage",
        "Ruddy Shelduck: alert behavior and inland water habitat",
        "Common Shelduck: coastal mudflats and distinctive markings",
    ],
    "geese": [
        "Bar-headed Goose: high-altitude Himalayan migration",
        "Greylag Goose: flock leadership and wetland grazing",
        "Greater White-fronted Goose: family bonds and tundra origins",
    ],
    "cranes_and_bustards": [
        "Common Crane: graceful flight and wetland stopovers",
        "Demoiselle Crane: challenging mountain migration and courtship dance",
        "Houbara Bustard: desert adaptation and stealthy behavior",
    ],
    "waterbirds": [
        "Greater Flamingo: filter feeding in saline lagoons",
        "Lesser Flamingo: alkaline lake ecology and flock movement",
        "Great White Pelican: cooperative fishing and soaring flight",
        "Dalmatian Pelican: massive wingspan and freshwater lakes",
        "Eurasian Spoonbill: sweeping bill motion in shallow waters",
        "Black Stork: solitary habits and quiet forest wetlands",
        "White Stork: long-distance thermals and wetland foraging",
    ],
    "cormorants_and_gulls": [
        "Black-headed Gull: agile flight and opportunistic feeding",
        "Brown-headed Gull: high-altitude breeding and seasonal plumage",
        "Common Cormorant: expert underwater fishing and wing drying",
        "Great Cormorant: deep diving and coastal roosting",
    ],
    "shorebirds": [
        "Eurasian Curlew: curved bill and coastal mudflat probing",
        "Common Snipe: camouflage in marshlands and zigzag flight",
        "Little Stint: endurance migration and rapid shoreline feeding",
        "Green Sandpiper: solitary foraging along freshwater margins",
        "Wood Sandpiper: marshland foraging and agile flight",
        "Common Greenshank: alert calls and active wetland hunting",
        "Black-tailed Godwit: deep-mud probing and long-distance flight",
        "Kentish Plover: nesting camouflage and sandy shore running",
    ],
    "passerines": [
        "Yellow Wagtail: tail pumping and grassland insect hunting",
        "White Wagtail: urban adaptability and energetic motion",
        "Barn Swallow: aerial insect hunting and long-distance journey",
        "Sand Martin: riverbank nesting colonies and agile swooping",
        "Bluethroat: skulking behavior in reeds and mimicry songs",
        "Common Starling: synchronized murmurations and winter flocks",
        "Common Chiffchaff: canopy insect foraging and rhythmic call",
    ],
    "raptors": [
        "Osprey: aerial hovering and precision fish hunting",
    ],
}

ORDER = [
    "ducks", "ducks", "geese", "ducks", "cranes_and_bustards",
    "waterbirds", "shorebirds", "cormorants_and_gulls", "passerines", "raptors",
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
