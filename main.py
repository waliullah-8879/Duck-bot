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
from footage import NoMatchingFootageError, fetch_clips  # noqa: E402
from script_gen import bird_search_terms, generate_script  # noqa: E402
from topics import mark_used, pick_topic  # noqa: E402
from tts import synthesize  # noqa: E402

OUT_DIR = Path(__file__).parent / "output"
SCHEDULED_TOPIC_ATTEMPTS = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="build video but do not post")
    ap.add_argument("--topic", help="override the topic")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="duckbot_"))
    skipped_topics = []
    try:
        attempts = 1 if args.topic else SCHEDULED_TOPIC_ATTEMPTS
        for attempt in range(attempts):
            category, topic = pick_topic(
                args.topic,
                exclude_species=skipped_topics,
                category_offset=attempt,
            )
            print(f"[topic] ({category}) {topic}")
            attempt_work = work / f"attempt_{attempt:02d}"
            attempt_work.mkdir()
            species = topic.split(":", 1)[0].strip()

            try:
                clips = fetch_clips(bird_search_terms(topic), attempt_work, species)
            except NoMatchingFootageError as exc:
                if args.topic:
                    raise
                print(f"[topic] {exc}; trying another species.")
                skipped_topics.append(topic)
                shutil.rmtree(attempt_work, ignore_errors=True)
                continue

            script = generate_script(topic)
            print(f"[script] {script['title']}")
            audio = Path(synthesize(script["narration"], str(attempt_work / "voice.mp3")))
            slug = "".join(c if c.isalnum() else "_" for c in script["title"])[:40]
            out = OUT_DIR / f"{slug}.mp4"
            build_video(clips, audio, attempt_work, out)
            print(f"[video] {out}")
            break
        else:
            raise RuntimeError(
                f"None of the next {SCHEDULED_TOPIC_ATTEMPTS} topics has enough tagged Pixabay footage; no video was posted."
            )
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
        mark_used(topic, also_used=skipped_topics)


if __name__ == "__main__":
    main()
