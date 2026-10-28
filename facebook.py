"""Publish a video to a Facebook Page via the Graph API."""
import os

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def post_video(path: str, title: str, description: str) -> dict:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_TOKEN"]
    with open(path, "rb") as fh:
        r = requests.post(
            f"{GRAPH}/{page_id}/videos",
            data={"title": title, "description": description, "access_token": token},
            files={"source": fh},
            timeout=600,
        )
    if r.status_code != 200:
        raise RuntimeError(f"Facebook upload failed: {r.status_code} {r.text}")
    return r.json()
