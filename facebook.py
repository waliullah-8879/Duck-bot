"""Publish a video or Reel to a Facebook Page via the Graph API."""
import io
import os
from pathlib import Path

import requests

GRAPH_API = "https://graph.facebook.com/v21.0"
GRAPH_VIDEO = "https://graph-video.facebook.com/v21.0"
CHUNK_SIZE = 8 * 1024 * 1024


def _post_video_request(url: str, *, data: dict, files=None) -> dict:
    try:
        response = requests.post(url, data=data, files=files, timeout=(30, 600))
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else "network error"
        raise RuntimeError(f"Facebook video upload request failed ({status}).") from None

    if not response.ok:
        raise RuntimeError(f"Facebook video upload failed with HTTP {response.status_code}: {response.text}")
    try:
        return response.json()
    except ValueError:
        raise RuntimeError("Facebook returned an invalid response during video upload.") from None


def post_reel(path: str, title: str, description: str) -> dict:
    """Upload and publish as an official Facebook Reel to maximize algorithmic reach."""
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_TOKEN"]
    video_path = Path(path)
    file_size = video_path.stat().st_size

    # Step 1: Initialize the Reel upload session
    endpoint = f"{GRAPH_API}/{page_id}/video_reels"
    start_resp = _post_video_request(
        endpoint,
        data={
            "access_token": token,
            "upload_phase": "start",
        },
    )
    video_id = start_resp.get("video_id")
    if not video_id:
        raise RuntimeError("Facebook did not return a Reel video ID.")
    upload_url = start_resp.get("upload_url") or f"https://rupload.facebook.com/video-upload/v21.0/{video_id}"

    # Step 2: Upload the binary video content
    headers = {
        "Authorization": f"OAuth {token}",
        "offset": "0",
        "file_size": str(file_size),
    }
    with video_path.open("rb") as f:
        try:
            upload_resp = requests.post(
                upload_url,
                headers=headers,
                data=f,
                timeout=(30, 600),
            )
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else "network error"
            raise RuntimeError(f"Reel binary upload failed ({status}).") from None

    if not upload_resp.ok:
        raise RuntimeError(f"Reel binary upload failed with HTTP {upload_resp.status_code}: {upload_resp.text}")

    # Step 3: Publish the Reel
    finish_data = {
        "access_token": token,
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "title": title,
        "description": description,
    }
    return _post_video_request(endpoint, data=finish_data)


def post_standard_video(path: str, title: str, description: str) -> dict:
    """Fallback: publish as a standard timeline video post."""
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_TOKEN"]
    video_path = Path(path)
    endpoint = f"{GRAPH_VIDEO}/{page_id}/videos"
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


def post_video(path: str, title: str, description: str) -> dict:
    """Publish the video, prioritizing Facebook Reels for viral reach with standard fallback."""
    try:
        print("[facebook] Publishing as Facebook Reel...")
        res = post_reel(path, title, description)
        print("[facebook] Successfully published as Facebook Reel!")
        return res
    except Exception as exc:
        print(f"[facebook] Reel publishing encountered issue ({exc}); falling back to standard video post.")
        return post_standard_video(path, title, description)
