"""Publish a video to a Facebook Page via the Graph API."""
import io
import os
from pathlib import Path

import requests

GRAPH = "https://graph-video.facebook.com/v26.0"
CHUNK_SIZE = 8 * 1024 * 1024


def _post_video_request(url: str, *, data: dict, files=None) -> dict:
    try:
        response = requests.post(url, data=data, files=files, timeout=(30, 600))
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else "network error"
        raise RuntimeError(f"Facebook video upload request failed ({status}).") from None

    if not response.ok:
        raise RuntimeError(f"Facebook video upload failed with HTTP {response.status_code}.")
    try:
        return response.json()
    except ValueError:
        raise RuntimeError("Facebook returned an invalid response during video upload.") from None


def post_video(path: str, title: str, description: str) -> dict:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_TOKEN"]
    video_path = Path(path)
    endpoint = f"{GRAPH}/{page_id}/videos"
    start = _post_video_request(
        endpoint,
        data={
            "access_token": token,
            "upload_phase": "start",
            "file_size": str(video_path.stat().st_size),
        },
    )
    session_id = start.get("upload_session_id")
    if not session_id:
        raise RuntimeError("Facebook did not return an upload session ID.")

    start_offset = int(start.get("start_offset", 0))
    end_offset = int(start.get("end_offset", video_path.stat().st_size))
    with video_path.open("rb") as video_file:
        while start_offset < end_offset:
            video_file.seek(start_offset)
            chunk = video_file.read(min(CHUNK_SIZE, end_offset - start_offset))
            if not chunk:
                raise RuntimeError("The video ended before Facebook's upload offset.")
            transferred = _post_video_request(
                endpoint,
                data={
                    "access_token": token,
                    "upload_phase": "transfer",
                    "upload_session_id": session_id,
                    "start_offset": str(start_offset),
                },
                files={"video_file_chunk": (video_path.name, io.BytesIO(chunk), "application/octet-stream")},
            )
            next_start = int(transferred.get("start_offset", -1))
            next_end = int(transferred.get("end_offset", -1))
            if next_start <= start_offset or next_end < next_start:
                raise RuntimeError("Facebook returned an invalid video upload offset.")
            start_offset, end_offset = next_start, next_end

    return _post_video_request(
        endpoint,
        data={
            "access_token": token,
            "upload_phase": "finish",
            "upload_session_id": session_id,
            "title": title,
            "description": description,
        },
    )
