"""Assemble a high-quality 1080x1920 vertical Reel from clips, narration, and atmospheric nature audio."""
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
TARGET_CUT_DURATION = 3.2  # Fast, high-retention viral cut length


def run(cmd: list[str], cwd: Path | None = None):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=cwd)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidate_fonts = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "Arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]
    for font_name in candidate_fonts:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_hook_badge(species: str, workdir: Path) -> Path:
    """Generate a sleek, modern on-screen header badge to hook viewers scrolling on mute."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    badge_w, badge_h = 860, 150
    bx = (W - badge_w) // 2
    by = 180  # Top upper third, clear of Facebook caption & UI icons

    # Dark frosted glass container with emerald border
    draw.rounded_rectangle(
        [bx, by, bx + badge_w, by + badge_h],
        radius=36,
        fill=(15, 23, 42, 215),
        outline=(52, 211, 153, 235),
        width=3,
    )

    species_clean = species.strip().upper()
    font_main = _load_font(42, bold=True)
    font_sub = _load_font(24, bold=True)

    # Sub-header
    draw.text(
        (bx + badge_w // 2, by + 42),
        "WILD SPECIES • INDUS FLYWAY",
        fill=(52, 211, 153, 255),
        font=font_sub,
        anchor="mm",
    )
    # Main species identifier
    draw.text(
        (bx + badge_w // 2, by + 95),
        species_clean,
        fill=(255, 255, 255, 255),
        font=font_main,
        anchor="mm",
    )

    overlay_path = workdir / "hook_badge.png"
    img.save(str(overlay_path))
    return overlay_path


def build_video(
    clips: list[Path],
    audio: Path,
    workdir: Path,
    out: Path,
    bg_audio: Path | None = None,
    species: str = "Wildlife",
) -> Path:
    if not clips:
        raise ValueError("At least one bird video clip is required.")
    total = duration(audio) + 0.3

    # Gather durations of all available unique clips
    clip_durations = [duration(c) for c in clips]

    # Build sequence of dynamic cuts (never repeating the same clip back-to-back)
    parts = []
    elapsed = 0.0
    clip_offsets = [0.0] * len(clips)
    cut_idx = 0

    while elapsed < total:
        remaining = total - elapsed
        c_i = cut_idx % len(clips)
        c_path = clips[c_i]
        c_dur = clip_durations[c_i]

        offset = clip_offsets[c_i]
        # Calculate available duration in this clip
        avail = max(0.5, c_dur - offset)
        cut_len = min(TARGET_CUT_DURATION, remaining, avail)

        # If clip ran out or is too short, reset offset for loop
        if cut_len < 1.0 or offset + cut_len >= c_dur:
            offset = 0.0
            clip_offsets[c_i] = 0.0
            avail = max(0.5, c_dur)
            cut_len = min(TARGET_CUT_DURATION, remaining, avail)

        p = workdir / f"part_{cut_idx:03d}.mp4"
        run([
            "ffmpeg", "-y", "-ss", f"{offset:.3f}", "-i", str(c_path), "-t", f"{cut_len:.3f}",
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(p),
        ])
        parts.append(p)
        clip_offsets[c_i] += cut_len
        elapsed += cut_len
        cut_idx += 1

    lst = workdir / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = workdir / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)], cwd=workdir)

    # Generate visual hook badge overlay
    badge_path = create_hook_badge(species, workdir)

    if bg_audio and Path(bg_audio).exists():
        # Mix voiceover with atmospheric nature sound (water & species calls) in background + visual hook badge
        cmd = [
            "ffmpeg", "-y",
            "-i", str(joined),
            "-i", str(audio),
            "-i", str(bg_audio),
            "-i", str(badge_path),
            "-filter_complex",
            "[0:v][3:v]overlay=0:0[vout];"
            "[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=1.20[v];"
            "[2:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.28[b];"
            "[v][b]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "[vout]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(out),
        ]
        run(cmd)
    else:
        # Single audio track (pure nature soundscape or voice) + visual hook badge
        cmd = [
            "ffmpeg", "-y",
            "-i", str(joined),
            "-i", str(audio),
            "-i", str(badge_path),
            "-filter_complex",
            "[0:v][2:v]overlay=0:0[vout];"
            "[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=1.15[a]",
            "-map", "[vout]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(out),
        ]
        run(cmd)

    return out
