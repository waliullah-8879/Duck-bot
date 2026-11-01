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
CACHE_VERSION = 3
MIN_SPECIES_CLIPS = 3
GROUP_SEARCH_TERMS = {
    "ducks": ["wild ducks waterfowl", "ducks swimming pond", "ducks flying lake"],
    "geese": ["wild geese waterfowl", "geese flying flock", "geese swimming lake"],
    "doves": ["doves flying flock", "wild pigeons perched", "doves feeding ground"],
}
GROUP_TAGS = {
    "ducks": {"duck", "ducks"},
    "geese": {"goose", "geese"},
    "doves": {"dove", "doves", "pigeon", "pigeons"},
}
NON_BIRD_TAGS = {"dog", "dogs", "puppy", "puppies", "cat", "cats", "kitten", "pet", "pets", "toy", "plush"}
SCIENTIFIC_NAME_ALIASES = {
    "common pochard": {"aythya ferina", "pochard"},
    "mallard duck": {"anas platyrhynchos", "mallard"},
    "green winged teal": {"anas crecca"},
    "wood duck": {"aix sponsa"},
    "northern pintail": {"anas acuta", "pintail"},
    "gadwall": {"mareca strepera"},
    "eurasian wigeon": {"mareca penelope"},
    "northern shoveler": {"spatula clypeata"},
    "common eider": {"somateria mollissima"},
    "common goldeneye": {"bucephala clangula", "goldeneye"},
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


def _matches_species(hit: dict, species: str) -> bool:
    tags = hit.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)
    normalized_tags = f" {_normalize_words(str(tags))} "
    normalized_species = _normalize_words(species)
    aliases = {normalized_species}
    aliases.update(SCIENTIFIC_NAME_ALIASES.get(normalized_species, set()))
    return any(alias and f" {alias} " in normalized_tags for alias in aliases)


def _matches_group(hit: dict, group: str) -> bool:
    allowed_tags = GROUP_TAGS.get(group)
    if not allowed_tags:
        return False
    tags = hit.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)
    normalized_tags = f" {_normalize_words(str(tags))} "
    if any(f" {tag} " in normalized_tags for tag in NON_BIRD_TAGS):
        return False
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
    cache_key = f"v{CACHE_VERSION}:{term.casefold()}:animals:200:{order}:safe"
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
