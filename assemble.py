"""Assemble a high-quality 1080x1920 video from clips and narration."""
import subprocess
from pathlib import Path

W, H, FPS = 1080, 1920, 30


def run(cmd: list[str], cwd: Path | None = None):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=cwd)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def build_video(clips: list[Path], audio: Path, workdir: Path, out: Path) -> Path:
    if not clips:
        raise ValueError("At least one bird video clip is required.")
    total = duration(audio) + 0.3
    seg = total / len(clips)

    parts = []
    for i, c in enumerate(clips):
        p = workdir / f"part_{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(c), "-t", f"{seg:.3f}",
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
            "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", str(p),
        ])
        parts.append(p)

    lst = workdir / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = workdir / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)], cwd=workdir)

    base = ["ffmpeg", "-y", "-i", str(joined), "-i", str(audio)]
    tail = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(out)]
    run(base + tail)
    return out
