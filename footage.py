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
    videos = hit.get("videos") or {}
    for variant in ("medium", "small", "tiny", "large"):
        video_file = videos.get(variant)
        if video_file and video_file.get("url"):
            return video_file
    return None


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


def fetch_clips(terms: list[str], workdir: Path, want: int = 12) -> list[Path]:
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
            if _download_clip(video_file["url"], dest):
                clips.append(dest)
    if not clips:
        raise RuntimeError("No stock clips found. Check PIXABAY_API_KEY / search terms.")
    return clips
