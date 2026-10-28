"""Daily wildlife video bot.

Usage:
    python main.py                 # make + post today's video
    python main.py --dry-run       # make the video only, do not post
    python main.py --topic "Mallard facts" --dry-run
"""
import argparse
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from assemble import build_video  # noqa: E402
from facebook import post_video  # noqa: E402
from footage import fetch_clips  # noqa: E402
from script_gen import generate_script  # noqa: E402
from topics import mark_used, pick_topic  # noqa: E402
from tts import synthesize  # noqa: E402

OUT_DIR = Path(__file__).parent / "output"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="build video but do not post")
    ap.add_argument("--topic", help="override the topic")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    category, topic = pick_topic(args.topic)
    print(f"[topic] ({category}) {topic}")

    script = generate_script(topic)
    print(f"[script] {script['title']}")

    work = Path(tempfile.mkdtemp(prefix="duckbot_"))
    try:
        audio = Path(synthesize(script["narration"], str(work / "voice.mp3")))
        clips = fetch_clips(script["search_terms"], work)
        slug = "".join(c if c.isalnum() else "_" for c in script["title"])[:40]
        out = OUT_DIR / f"{slug}.mp4"
        build_video(clips, audio, script["narration"], work, out)
        print(f"[video] {out}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if args.dry_run:
        print("[dry-run] Skipping Facebook upload.")
        return

    tags = " ".join("#" + t.lstrip("#") for t in script["hashtags"])
    desc = f"{script['narration']}\n\n{tags}\n\nVideo clips: Pixabay."
    result = post_video(str(out), script["title"], desc)
    print(f"[facebook] Posted: {result}")
    if not args.topic:
        mark_used(topic)


if __name__ == "__main__":
    main()
