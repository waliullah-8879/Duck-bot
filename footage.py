"""Download stock video clips from Pixabay (https://pixabay.com/api/docs/)."""
import hashlib
import json
import os
from pathlib import Path
import time

import requests

API = "https://pixabay.com/api/videos/"
CACHE_DIR = Path(__file__).parent / ".cache" / "pixabay"
CACHE_TTL = 24 * 60 * 60


def _best_file(hit: dict):
    files = [f for f in (hit.get("videos") or {}).values() if f.get("url")]
    if not files:
        return None

    def score(f):
        w, h = f.get("width") or 0, f.get("height") or 0
        target_w, target_h = (1080, 1920) if h > w else (1920, 1080)
        return (h > w, min(w, h) >= 720, -(abs(w - target_w) + abs(h - target_h)))

    return sorted(files, key=score, reverse=True)[0]


def _search_videos(term: str, key: str) -> dict:
    cache_name = hashlib.sha256(term.casefold().encode("utf-8")).hexdigest() + ".json"
    cache_file = CACHE_DIR / cache_name
    try:
        if time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass

    try:
        response = requests.get(
            API,
            params={"key": key, "q": term, "category": "animals", "per_page": 5, "safesearch": "true"},
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


def fetch_clips(terms: list[str], workdir: Path, want: int = 6) -> list[Path]:
    key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set PIXABAY_API_KEY in your .env file before downloading footage.")

    clips: list[Path] = []
    seen: set[int] = set()
    for term in terms:
        if len(clips) >= want:
            break
        for hit in _search_videos(term, key).get("hits", []):
            video_id = hit.get("id")
            if video_id is None or video_id in seen or len(clips) >= want:
                continue
            video_file = _best_file(hit)
            if not video_file:
                continue
            seen.add(video_id)
            dest = workdir / f"clip_{len(clips):02d}.mp4"
            with requests.get(video_file["url"], stream=True, timeout=120) as dl:
                dl.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in dl.iter_content(1 << 20):
                        fh.write(chunk)
            clips.append(dest)
            break  # one clip per search term keeps variety
    if not clips:
        raise RuntimeError("No stock clips found. Check PIXABAY_API_KEY / search terms.")
    return clips
