"""Assemble a high-quality 1080x1920 video from clips and narration/nature audio with dynamic pacing."""
import subprocess
from pathlib import Path

W, H, FPS = 1080, 1920, 30
TARGET_CUT_DURATION = 3.5  # Dynamic, viral cut length (seconds per shot)


def run(cmd: list[str], cwd: Path | None = None):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=cwd)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def build_video(clips: list[Path], audio: Path, workdir: Path, out: Path, bg_audio: Path | None = None) -> Path:
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
        cut_len = min(TARGET_CUT_DURATION, remaining)
        c_i = cut_idx % len(clips)
        c_path = clips[c_i]
        c_dur = clip_durations[c_i]

        offset = clip_offsets[c_i]
        # If remaining portion of this clip is too short for a clean cut, reset offset
        if offset + cut_len > c_dur:
            offset = 0.0
            clip_offsets[c_i] = 0.0

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

    if bg_audio and Path(bg_audio).exists():
        # Mix voiceover with atmospheric nature sound in background
        cmd = [
            "ffmpeg", "-y", "-i", str(joined), "-i", str(audio), "-i", str(bg_audio),
            "-filter_complex", "[1:a]volume=1.0[v];[2:a]volume=0.35[b];[v][b]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(out),
        ]
        run(cmd)
    else:
        # Single audio track (pure nature soundscape or voice)
        base = ["ffmpeg", "-y", "-i", str(joined), "-i", str(audio)]
        tail = ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(out)]
        run(base + tail)

    return out
