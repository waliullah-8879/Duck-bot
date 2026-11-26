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
CACHE_VERSION = 5
MIN_SPECIES_CLIPS = 5

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
    # Holiday / novelty / comical / dance themes
    "santa", "christmas", "xmas", "dancing", "dance", "fitness",
    "holiday", "festive", "decoration", "decorative", "ornament",
    # Domestic pets & non-birds
    "dog", "dogs", "puppy", "puppies", "cat", "cats", "kitten", "kittens", "pet", "pets",
    # Culinary / food
    "recipe", "roast", "cooked", "cooking", "meat", "dish",
}

# Hard-coded Pixabay clip IDs that are known cartoons/animations regardless of their tags.
BLOCKED_CLIP_IDS: set[int] = {
    385453,  # 3D yellow dancing duck with Santa hat
    385454,  # 3D green mallard duck with Santa hat
}

SCIENTIFIC_NAME_ALIASES = {
    # Ducks & Waterfowl
    "mallard": {"anas platyrhynchos", "mallard duck", "mallard", "wild duck", "drake"},
    "wood duck": {"aix sponsa", "wood duck", "carolina duck"},
    "mandarin duck": {"aix galericulata", "mandarin duck", "mandarin"},
    "common merganser": {"mergus merganser", "goosander", "merganser"},
    "common teal": {"anas crecca", "eurasian teal", "teal duck", "green winged teal"},
    "tufted duck": {"aythya fuligula", "tufted duck"},
    # Geese & Swans
    "canada goose": {"branta canadensis", "canada goose", "canadian goose"},
    "greylag goose": {"anser anser", "graylag goose", "greylag goose", "greylag"},
    "egyptian goose": {"alopochen aegyptiaca", "egyptian goose"},
    "black swan": {"cygnus atratus", "black swan"},
    "mute swan": {"cygnus olor", "mute swan", "white swan"},
    # Waterbirds & Waders
    "greater flamingo": {"phoenicopterus roseus", "flamingo", "flamingos"},
    "great white pelican": {"pelecanus onocrotalus", "white pelican", "pelican"},
    "dalmatian pelican": {"pelecanus crispus", "dalmatian pelican", "pelican"},
    "white stork": {"ciconia ciconia", "white stork", "stork", "storks"},
    "black stork": {"ciconia nigra", "black stork"},
    "grey heron": {"ardea cinerea", "grey heron", "gray heron", "heron"},
    "great egret": {"ardea alba", "great egret", "white egret", "egret"},
    "common kingfisher": {"alcedo atthis", "kingfisher", "common kingfisher"},
    # Cormorants
    "common cormorant": {"phalacrocorax carbo", "great cormorant", "cormorant"},
    "great cormorant": {"phalacrocorax carbo", "great cormorant", "cormorant"},
    # Passerines
    "yellow wagtail": {"motacilla flava", "western yellow wagtail", "yellow wagtail", "wagtail"},
    "white wagtail": {"motacilla alba", "white wagtail", "wagtail"},
    "barn swallow": {"hirundo rustica", "barn swallow", "swallow"},
    "common starling": {"sturnus vulgaris", "european starling", "starling"},
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


def _search_videos(term: str, key: str, order: str, retries: int = 3) -> dict:
    cache_key = f"v{CACHE_VERSION}:{term.casefold()}:film:animals:200:{order}:safe"
    cache_name = hashlib.sha256(cache_key.encode("utf-8")).hexdigest() + ".json"
    cache_file = CACHE_DIR / cache_name
    try:
        if time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass

    for attempt in range(retries):
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
            data = response.json()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            return data
        except requests.RequestException as exc:
            if attempt + 1 == retries:
                status = exc.response.status_code if exc.response is not None else "network error"
                raise RuntimeError(f"Pixabay video search failed ({status}); check PIXABAY_API_KEY and network access.") from None
            time.sleep(1.5 * (attempt + 1))


def fetch_clips(terms: list[str], workdir: Path, species: str, group: str = "", want: int = 12) -> list[Path]:
    """Download authentic wildlife video clips strictly matching the topic species.
    
    NEVER downloads generic or unmatched birds. If fewer than MIN_SPECIES_CLIPS
    exact clips are found, raises NoMatchingFootageError so main.py tries the next topic.
    """
    key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set PIXABAY_API_KEY in your .env file before downloading footage.")

    clips: list[Path] = []
    seen: set[int] = set()

    def collect(search_terms: list[str]) -> None:
        for order in ("popular", "latest"):
            for term in search_terms:
                if len(clips) >= want:
                    return
                for hit in _search_videos(term, key, order).get("hits", []):
                    video_id = hit.get("id")
                    if video_id is None or video_id in seen or len(clips) >= want:
                        continue
                    if not _is_real_wildlife_video(hit):
                        continue
                    if not _matches_species(hit, species):
                        continue
                    video_file = _best_file(hit)
                    if not video_file:
                        continue
                    seen.add(video_id)
                    dest = workdir / f"clip_{len(clips):02d}.mp4"
                    if _download_clip(video_file["url"], dest):
                        clips.append(dest)

    collect(terms)

    if len(clips) < MIN_SPECIES_CLIPS:
        raise NoMatchingFootageError(
            f"Pixabay returned only {len(clips)} exact wildlife clips for {species!r}; "
            f"at least {MIN_SPECIES_CLIPS} exact clips are required to guarantee no unmatched footage."
        )

    print(f"[footage] Collected {len(clips)} authentic clips matching {species!r} exclusively.")
    return clips
