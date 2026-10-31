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
MIN_SPECIES_CLIPS = 4
GENERIC_SPECIES_WORDS = {"duck", "goose", "dove", "pigeon"}
SCIENTIFIC_NAME_ALIASES = {
    "common pochard": {"aythya ferina"},
    "mallard duck": {"anas platyrhynchos"},
    "green winged teal": {"anas crecca"},
    "wood duck": {"aix sponsa"},
    "northern pintail": {"anas acuta"},
    "gadwall": {"mareca strepera"},
    "eurasian wigeon": {"mareca penelope"},
    "northern shoveler": {"spatula clypeata"},
    "common eider": {"somateria mollissima"},
    "common goldeneye": {"bucephala clangula"},
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

    words = normalized_species.split()
    if words and words[-1] in GENERIC_SPECIES_WORDS:
        core = " ".join(words[:-1])
        if len(core.split()) > 1 or len(core) >= 5:
            aliases.add(core)
    elif words and len(words[-1]) >= 5:
        aliases.add(words[-1])

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


def fetch_clips(terms: list[str], workdir: Path, species: str, want: int = 12) -> list[Path]:
    key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set PIXABAY_API_KEY in your .env file before downloading footage.")

    clips: list[Path] = []
    seen: set[int] = set()
    for order in ("latest", "popular"):
        for term in terms:
            if len(clips) >= want:
                break
            for hit in _search_videos(term, key, order).get("hits", []):
                video_id = hit.get("id")
                if video_id is None or video_id in seen or len(clips) >= want:
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
    minimum = min(MIN_SPECIES_CLIPS, want)
    if len(clips) < minimum:
        raise NoMatchingFootageError(
            f"Pixabay returned only {len(clips)} clips tagged for {species!r}; "
            f"at least {minimum} are required. No unrelated footage was used."
        )
    return clips
