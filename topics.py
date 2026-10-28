"""Topic pool + simple no-repeat rotation."""
import json
import random
from pathlib import Path

HISTORY = Path(__file__).parent / "history.json"

TOPICS = {
    "duck_species": [
        "Mallard: the most recognizable duck in the world",
        "Wood duck: North America's most colorful waterfowl",
        "Northern pintail: the elegant long-necked duck",
        "Canvasback: the fastest diving duck",
        "Green-winged teal: the smallest dabbling duck",
        "Blue-winged teal: the early migrant",
        "Gadwall: the understated gray duck",
        "American wigeon: the baldpate",
        "Northern shoveler: the duck with the spoon bill",
        "Bufflehead: the tiny diving duck",
        "Common goldeneye: the whistling-wing diver",
        "Redhead duck: the bright-eyed diver",
        "Mandarin duck: the ornamental beauty",
        "Harlequin duck: the whitewater specialist",
        "Muscovy duck: the perching duck of the tropics",
    ],
    "duck_hunting": [
        "How waterfowl hunting funds wetland conservation (Duck Stamps)",
        "Duck hunting safety: the rules every hunter follows",
        "Dabbling ducks vs diving ducks: how hunters tell them apart",
        "Why decoy spreads work: the psychology of ducks",
        "Understanding flyways: how ducks migrate across continents",
        "Steel shot vs lead: why non-toxic shot is required for waterfowl",
        "Duck calls explained: quack, feed chuckle and comeback call",
        "Retrievers in the duck blind: why Labs are the classic choice",
        "How hunting seasons and bag limits are set from population surveys",
        "Hunter education: what new waterfowl hunters learn first",
    ],
    "wild_hunting": [
        "Whitetail deer: the most hunted big game animal in North America",
        "Wild turkey: the conservation comeback story",
        "Elk bugling season: what the sound means",
        "Pheasant hunting and upland bird habitat",
        "Hunting ethics: fair chase explained",
        "How hunters fund wildlife conservation (the Pittman-Robertson Act)",
        "Moose: giants of the northern forests",
        "Wild boar: an invasive species and why management matters",
        "Mule deer vs whitetail: spotting the differences",
        "Canada geese: from near extinction to everywhere",
    ],
    "wildlife": [
        "Bald eagle: from endangered to recovered",
        "How migratory birds navigate thousands of miles",
        "Beavers: nature's engineers",
        "Great horned owl: the silent night hunter",
        "Sandhill cranes and the great spring gathering",
        "Wolves and the Yellowstone effect",
        "Why wetlands are among the most valuable ecosystems on Earth",
        "Swans: mute, trumpeter and tundra compared",
        "Osprey: the master fish-catcher",
        "Pelicans: the plunge-diving giants",
        "Otters: the playful river hunters",
        "Black bears: myths vs facts",
    ],
}

ORDER = ["duck_species", "wildlife", "duck_hunting", "wild_hunting"]


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
