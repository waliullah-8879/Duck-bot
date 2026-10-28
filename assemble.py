"""Assemble a 1080x1920 video with ffmpeg: clips + narration + burned-in captions."""
import re
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


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def make_srt(text: str, total: float, out: Path):
    """Split narration into short caption chunks, timed proportionally to length."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks = []
    for s in sentences:
        words = s.split()
        for i in range(0, len(words), 6):
            chunks.append(" ".join(words[i:i + 6]))
    total_chars = sum(len(c) for c in chunks) or 1
    t, lines = 0.0, []
    for i, c in enumerate(chunks, 1):
        d = total * len(c) / total_chars
        lines.append(f"{i}\n{_srt_time(t)} --> {_srt_time(t + d)}\n{c}\n")
        t += d
    out.write_text("\n".join(lines), encoding="utf-8")


def build_video(clips: list[Path], audio: Path, narration: str, workdir: Path, out: Path) -> Path:
    total = duration(audio) + 0.6
    seg = total / len(clips)

    # 1) normalise each clip to 1080x1920 and trim to its share of the narration
    parts = []
    for i, c in enumerate(clips):
        p = workdir / f"part_{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(c), "-t", f"{seg:.3f}",
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", str(p),
        ])
        parts.append(p)

    # 2) concatenate
    lst = workdir / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    joined = workdir / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])

    # 3) add narration (+ captions if ffmpeg has libass)
    srt = workdir / "captions.srt"
    make_srt(narration, total - 0.6, srt)
    style = "FontSize=14,Bold=1,Outline=2,Alignment=2,MarginV=180,PrimaryColour=&H00FFFFFF"
    base = ["ffmpeg", "-y", "-i", str(joined), "-i", str(audio)]
    tail = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(out)]
    try:
        run(base + ["-vf", f"subtitles={srt.name}:force_style='{style}'"] + tail, cwd=workdir)
    except subprocess.CalledProcessError:
        print("[assemble] Captions unavailable, rendering without subtitles.")
        run(base + tail)
    return out
