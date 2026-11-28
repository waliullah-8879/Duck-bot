"""Daily wildlife video bot.

Usage:
    python main.py                           # make + post today's video (nature audio default)
    python main.py --dry-run                 # make the video only, do not post
    python main.py --audio-mode mixed        # voiceover + natural water/species sounds in background
    python main.py --audio-mode nature       # authentic species sound + natural water and birds
    python main.py --topic "Mallard facts" --dry-run
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from dotenv import load_dotenv

load_dotenv()

from assemble import build_video  # noqa: E402
from audio_nature import synthesize_nature_audio  # noqa: E402
from facebook import post_video  # noqa: E402
from footage import NoMatchingFootageError, fetch_clips  # noqa: E402
from image_map import get_reference_image  # noqa: E402
from script_gen import bird_search_terms, generate_script  # noqa: E402
from topics import mark_used, pick_topic  # noqa: E402
from tts import synthesize  # noqa: E402
from verify_image import verify_species_image  # noqa: E402

OUT_DIR = Path(__file__).parent / "output"
SCHEDULED_TOPIC_ATTEMPTS = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="build video but do not post")
    ap.add_argument("--topic", help="override the topic")
    ap.add_argument(
        "--audio-mode",
        choices=["nature", "mixed", "voice"],
        default=os.getenv("AUDIO_MODE", "mixed"),
        help="audio soundtrack: 'mixed' (strong voice + natural water & authentic species calls), 'nature', or 'voice'",
    )
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
                clips = fetch_clips(bird_search_terms(topic), attempt_work, species, category)
            except NoMatchingFootageError as exc:
                if args.topic:
                    raise
                print(f"[topic] {exc}; trying another species.")
                skipped_topics.append(topic)
                shutil.rmtree(attempt_work, ignore_errors=True)
                continue

            # --- Image verification: compare first clip against reference ---
            ref_img = get_reference_image(species)
            if clips and not verify_species_image(species, ref_img, clips[0]):
                print(f"[verify] {species}: verification FAILED — trying next species.")
                skipped_topics.append(topic)
                shutil.rmtree(attempt_work, ignore_errors=True)
                continue

            # Generate dynamic, non-repeating title, caption description and hashtags
            script = generate_script(topic)
            print(f"[script] {script['title']}")

            mode = args.audio_mode.lower()
            print(f"[audio] Selected audio mode: {mode}")

            if mode == "nature":
                # Authentic species calls + natural water ripples/splashes + ambient wetland birds
                target_dur = float(os.getenv("VIDEO_DURATION", "40.0"))
                audio = Path(synthesize_nature_audio(species, target_dur, attempt_work / "nature.mp3"))
                bg_audio = None
            elif mode == "mixed":
                # Narration voiceover + atmospheric species calls & water sounds in background
                voice_audio = Path(synthesize(script["narration"], str(attempt_work / "voice.mp3")))
                dur_out = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(voice_audio)],
                    capture_output=True, text=True, check=True,
                ).stdout.strip()
                v_dur = float(dur_out) if dur_out else 40.0
                nature_audio = synthesize_nature_audio(species, v_dur + 0.5, attempt_work / "nature.mp3")
                audio = voice_audio
                bg_audio = Path(nature_audio)
            else:
                # Narration voice only
                audio = Path(synthesize(script["narration"], str(attempt_work / "voice.mp3")))
                bg_audio = None

            slug = "".join(c if c.isalnum() else "_" for c in script["title"])[:40]
            out = OUT_DIR / f"{slug}.mp4"
            build_video(clips, audio, attempt_work, out, bg_audio=bg_audio, species=species)
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

    species_raw = topic.split(":", 1)[0].strip()
    tags = " ".join("#" + t.lstrip("#") for t in script["hashtags"])
    desc = (
        f"{script['title']}\n\n"
        f"🌍 International Wildlife & Waterfowl Spotlight:\n"
        f"• Species: {species_raw} | Family: Anatidae (Wild Waterfowl)\n"
        f"• Flyway: Indus Flyway (International Migratory Route 4)\n"
        f"• Habitat: Wild wetlands, freshwater lakes, and marshes\n"
        f"• Status: 100% Authentic Wild Footage • Natural Habitat\n\n"
        f"{script['narration']}\n\n"
        f"🎯 Follow for daily wild duck, waterfowl & hunting species reels!\n"
        f"💬 Have you ever spotted or called a {species_raw} in the wild? Share your sightings below!\n\n"
        f"{tags}\n\n"
        f"Footage: Authentic wildlife stock (Pixabay)."
    )
    result = post_video(str(out), script["title"], desc)
    print(f"[facebook] Posted: {result}")
    if not args.topic:
        mark_used(topic, also_used=skipped_topics)


if __name__ == "__main__":
    main()
