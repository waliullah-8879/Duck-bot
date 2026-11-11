"""Download stock video clips from Pixabay (https://pixabay.com/api/docs/)."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

import requests

API = "https://pixabay.com/api/videos/"
CACHE_DIR = Path(__file__).parent / ".cache" / "pixabay"
CACHE_TTL = 24 * 60 * 60
CACHE_VERSION = 4
MIN_SPECIES_CLIPS = 3
GROUP_SEARCH_TERMS = {
    "ducks": ["wild ducks waterfowl", "ducks swimming pond", "ducks flying lake"],
    "geese": ["wild geese waterfowl", "geese flying flock", "geese swimming lake"],
    "cranes_and_bustards": ["crane bird flying wetland", "cranes flock lake", "bustard bird wildlife"],
    "waterbirds": ["flamingo flock water", "pelican swimming lake", "stork bird wetland", "spoonbill bird"],
    "cormorants_and_gulls": ["cormorant bird water", "seagulls flying sea", "gull bird coast"],
    "shorebirds": ["shorebird sandpiper wetland", "curlew bird mudflat", "snipe bird marsh", "plover bird beach"],
    "passerines": ["wagtail bird nature", "swallow bird flying", "songbird branch wildlife", "starling flock"],
    "raptors": ["osprey bird flight", "fish eagle raptor", "osprey catching fish"],
}
GROUP_TAGS = {
    "ducks": {"duck", "ducks", "waterfowl", "shelduck", "teal", "pochard", "wigeon", "mallard"},
    "geese": {"goose", "geese"},
    "cranes_and_bustards": {"crane", "cranes", "bustard"},
    "waterbirds": {"flamingo", "flamingos", "pelican", "pelicans", "stork", "storks", "spoonbill"},
    "cormorants_and_gulls": {"cormorant", "cormorants", "gull", "gulls", "seagull", "seagulls"},
    "shorebirds": {"sandpiper", "curlew", "snipe", "plover", "godwit", "stint", "greenshank", "shorebird", "wader"},
    "passerines": {"wagtail", "swallow", "martin", "starling", "bluethroat", "chiffchaff", "songbird"},
    "raptors": {"osprey", "raptor", "eagle", "hawk"},
}
EXCLUDED_TAGS = {
    # Animation, 3D CGI, renders, cartoons
    "animation", "animated", "cartoon", "cartoons", "3d", "cgi", "render", "rendered",
    "rendering", "illustration", "drawing", "vector", "graphic", "graphics", "motion graphics",
    "character", "characters", "puppet", "mascot", "costume", "model", "claymation",
    "origami", "figure", "figurine", "statue", "sculpture", "clipart",
    # Toys, plush, fake/artificial items
    "toy", "toys", "plush", "stuffed", "rubber duck", "bath toy", "fake", "artificial",
    # AI generated / synthetic
    "ai generated", "synthetic",
    # Holiday / novelty / comical / dance themes (like dancing Santa duck)
    "santa", "christmas", "xmas", "dancing", "dance", "fitness",
    "holiday", "festive", "decoration", "decorative", "ornament",
    # Domestic pets & non-birds
    "dog", "dogs", "puppy", "puppies", "cat", "cats", "kitten", "kittens", "pet", "pets",
    # Culinary / food
    "recipe", "roast", "cooked", "cooking", "meat", "dish",
}
# Hard-coded Pixabay clip IDs that are known cartoons/animations regardless of their tags.
# Add any new offending clip IDs here to permanently block them.
BLOCKED_CLIP_IDS: set[int] = {
    385453,  # 3D yellow dancing duck with Santa hat
    385454,  # 3D green mallard duck with Santa hat
}
SCIENTIFIC_NAME_ALIASES = {
    # Ducks & Waterfowl
    "mallard": {"anas platyrhynchos", "mallard duck"},
    "northern pintail": {"anas acuta", "pintail", "pintail duck"},
    "northern shoveler": {"spatula clypeata", "shoveler", "shoveler duck", "anas clypeata"},
    "common teal": {"anas crecca", "eurasian teal", "teal", "green winged teal"},
    "eurasian wigeon": {"mareca penelope", "wigeon", "anas penelope"},
    "gadwall": {"mareca strepera", "anas strepera"},
    "common pochard": {"aythya ferina", "pochard"},
    "red-crested pochard": {"netta rufina", "red crested pochard"},
    "tufted duck": {"aythya fuligula"},
    "garganey": {"spatula querquedula", "anas querquedula"},
    "ruddy shelduck": {"tadorna ferruginea", "brahminy duck"},
    "common shelduck": {"tadorna tadorna", "shelduck"},
    # Geese
    "bar-headed goose": {"anser indicus", "bar headed goose"},
    "greylag goose": {"anser anser", "graylag goose"},
    "greater white-fronted goose": {"anser albifrons", "white-fronted goose"},
    # Cranes & Bustards
    "common crane": {"grus grus", "eurasian crane"},
    "demoiselle crane": {"anthropoides virgo", "grus virgo"},
    "houbara bustard": {"chlamydotis macqueenii", "chlamydotis undulata", "asian houbara", "bustard"},
    # Waterbirds
    "greater flamingo": {"phoenicopterus roseus", "flamingo"},
    "lesser flamingo": {"phoeniconaias minor", "flamingo"},
    "great white pelican": {"pelecanus onocrotalus", "white pelican", "pelican"},
    "dalmatian pelican": {"pelecanus crispus", "pelican"},
    "eurasian spoonbill": {"platalea leucorodia", "spoonbill"},
    "black stork": {"ciconia nigra"},
    "white stork": {"ciconia ciconia", "stork"},
    # Cormorants & Gulls
    "black-headed gull": {"chroicocephalus ridibundus", "larus ridibundus", "black headed gull"},
    "brown-headed gull": {"chroicocephalus brunnicephalus", "larus brunnicephalus", "brown headed gull"},
    "common cormorant": {"phalacrocorax carbo", "great cormorant", "cormorant"},
    "great cormorant": {"phalacrocorax carbo", "common cormorant", "cormorant"},
    # Shorebirds
    "eurasian curlew": {"numenius arquata", "curlew"},
    "common snipe": {"gallinago gallinago", "snipe"},
    "little stint": {"calidris minuta", "stint"},
    "green sandpiper": {"tringa ochropus", "sandpiper"},
    "wood sandpiper": {"tringa glareola", "sandpiper"},
    "common greenshank": {"tringa nebularia", "greenshank"},
    "black-tailed godwit": {"limosa limosa", "godwit"},
    "kentish plover": {"charadrius alexandrinus", "plover"},
    # Passerines
    "yellow wagtail": {"motacilla flava", "western yellow wagtail", "wagtail"},
    "white wagtail": {"motacilla alba", "wagtail"},
    "barn swallow": {"hirundo rustica", "swallow"},
    "sand martin": {"riparia riparia", "bank swallow"},
    "bluethroat": {"luscinia svecica"},
    "common starling": {"sturnus vulgaris", "european starling", "starling"},
    "common chiffchaff": {"phylloscopus collybita", "chiffchaff"},
    # Raptors
    "osprey": {"pandion haliaetus", "western osprey", "fish hawk"},
}


class NoMatchingFootageError(RuntimeError):
    pass


def _best_file(hit: dict):
    videos = hit.get("videos") or {}
    for variant in ("medium", "small", "tiny", "large"):
        video_file = videos.get(variant)
        if video_file and video_file.get("url"):
            return video_file
    return None


def _normalize_words(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _is_real_wildlife_video(hit: dict) -> bool:
    # Hard-block known cartoon/animation clip IDs regardless of their metadata.
    if hit.get("id") in BLOCKED_CLIP_IDS:
        return False
    video_type = str(hit.get("type", "")).strip().lower()
    if video_type and video_type != "film":
        return False
    if hit.get("isAiGenerated"):
        return False

    tags = hit.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)
    all_text = f"{tags} {hit.get('name', '')} {hit.get('description', '')}"
    normalized = f" {_normalize_words(all_text)} "
    if any(f" {tag} " in normalized for tag in EXCLUDED_TAGS):
        return False
    return True


def _matches_species(hit: dict, species: str) -> bool:
    if not _is_real_wildlife_video(hit):
        return False
    tags = hit.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)
    normalized_tags = f" {_normalize_words(str(tags))} "
    normalized_species = _normalize_words(species)
    aliases = {normalized_species}
    aliases.update(SCIENTIFIC_NAME_ALIASES.get(normalized_species, set()))
    return any(alias and f" {alias} " in normalized_tags for alias in aliases)


def _matches_group(hit: dict, group: str) -> bool:
    if not _is_real_wildlife_video(hit):
        return False
    allowed_tags = GROUP_TAGS.get(group)
    if not allowed_tags:
        return False
    tags = hit.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)
    normalized_tags = f" {_normalize_words(str(tags))} "
    return any(f" {tag} " in normalized_tags for tag in allowed_tags)


def _download_clip(url: str, dest: Path, attempts: int = 3) -> bool:
    for attempt in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=(15, 120)) as response:
                response.raise_for_status()
                with dest.open("wb") as fh:
                    for chunk in response.iter_content(1 << 20):
                        if chunk:
                            fh.write(chunk)
            if dest.stat().st_size:
                return True
        except requests.RequestException:
            pass

        dest.unlink(missing_ok=True)
        if attempt + 1 < attempts:
            print(f"[footage] Download interrupted; retrying ({attempt + 1}/{attempts - 1}).")
            time.sleep(2 ** attempt)
    return False


def _search_videos(term: str, key: str, order: str) -> dict:
    cache_key = f"v{CACHE_VERSION}:{term.casefold()}:film:animals:200:{order}:safe"
    cache_name = hashlib.sha256(cache_key.encode("utf-8")).hexdigest() + ".json"
    cache_file = CACHE_DIR / cache_name
    try:
        if time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass

    try:
        response = requests.get(
            API,
            params={
                "key": key,
                "q": term,
                "video_type": "film",
                "category": "animals",
                "per_page": 200,
                "order": order,
                "safesearch": "true",
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else "network error"
        raise RuntimeError(f"Pixabay video search failed ({status}); check PIXABAY_API_KEY and network access.") from None

    data = response.json()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return data


def fetch_clips(terms: list[str], workdir: Path, species: str, group: str = "", want: int = 12) -> list[Path]:
    key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set PIXABAY_API_KEY in your .env file before downloading footage.")

    clips: list[Path] = []
    seen: set[int] = set()

    def collect(search_terms: list[str], matcher) -> None:
        for order in ("latest", "popular"):
            for term in search_terms:
                if len(clips) >= want:
                    return
                for hit in _search_videos(term, key, order).get("hits", []):
                    video_id = hit.get("id")
                    if video_id is None or video_id in seen or len(clips) >= want:
                        continue
                    if not _is_real_wildlife_video(hit):
                        continue
                    if not matcher(hit):
                        continue
                    video_file = _best_file(hit)
                    if not video_file:
                        continue
                    seen.add(video_id)
                    dest = workdir / f"clip_{len(clips):02d}.mp4"
                    if _download_clip(video_file["url"], dest):
                        clips.append(dest)

    collect(terms, lambda hit: _matches_species(hit, species))
    exact_count = len(clips)
    minimum = min(MIN_SPECIES_CLIPS, want)
    if len(clips) < minimum and group in GROUP_SEARCH_TERMS:
        collect(GROUP_SEARCH_TERMS[group], lambda hit: _matches_group(hit, group))

    if len(clips) < minimum:
        related_count = len(clips) - exact_count
        raise NoMatchingFootageError(
            f"Pixabay returned {exact_count} exact and {related_count} related {group or 'same-species'} clips "
            f"for {species!r}; at least {minimum} are required. No unrelated pets or bird groups were used."
        )
    related_count = len(clips) - exact_count
    if related_count:
        print(f"[footage] Using {related_count} related {group} clips and {exact_count} exact {species} clips.")
    return clips
