"""Species-image verification using perceptual hashing.

Usage
-----
    from verify_image import verify_species_image

    passed = verify_species_image("Mallard", ref_path, clip_path)
    if not passed:
        # skip this run
        ...

The function extracts the first frame of the given video clip, converts
both frames to greyscale, computes pHash via *imagehash*, and returns
True when the similarity is above SIMILARITY_THRESHOLD.

If *imagehash* or *Pillow* is not installed the function always returns
True with a warning so the pipeline does not break on first run.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

LOG = logging.getLogger(__name__)
SIMILARITY_THRESHOLD = 20  # max pHash distance to consider "similar" (0 = identical, 64 = totally different)

# ---------------------------------------------------------------------------
# Optional imports — degrade gracefully if the libraries are missing
# ---------------------------------------------------------------------------
try:
    from PIL import Image
    import imagehash
    _HAS_HASH = True
except ImportError:
    _HAS_HASH = False
    LOG.warning(
        "[verify] pillow / imagehash not installed — species verification disabled. "
        "Run:  pip install pillow imagehash"
    )


def _extract_first_frame(video_path: Path, out_path: Path) -> bool:
    """Use ffmpeg to grab the very first frame of *video_path* as a JPEG."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(out_path),
            ],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0 and out_path.exists()
    except Exception as exc:  # noqa: BLE001
        LOG.warning("[verify] ffmpeg frame-extract failed: %s", exc)
        return False


def verify_species_image(
    species: str,
    ref_path: Path | None,
    clip_path: Path | str,
) -> bool:
    """Return True if the clip visually resembles the reference image.

    Parameters
    ----------
    species:   Human-readable species name (used only for logging).
    ref_path:  Path to the user-supplied reference JPEG/PNG, or None.
    clip_path: Path to the downloaded Pixabay MP4 clip.

    Returns
    -------
    True  — verification passed (or was skipped because ref_path is None).
    False — hash distance exceeds threshold (looks wrong).
    """
    if not _HAS_HASH:
        LOG.warning("[verify] Libraries missing — skipping verification for %s.", species)
        return True

    if ref_path is None:
        LOG.info("[verify] No reference image for %s — skipping verification.", species)
        return True

    if not Path(ref_path).exists():
        LOG.warning("[verify] Reference image not found: %s — skipping.", ref_path)
        return True

    clip_path = Path(clip_path)
    with tempfile.TemporaryDirectory(prefix="duckbot_verify_") as tmp:
        frame_path = Path(tmp) / "frame.jpg"
        if not _extract_first_frame(clip_path, frame_path):
            LOG.warning("[verify] Could not extract frame from %s — skipping.", clip_path.name)
            return True

        try:
            ref_hash  = imagehash.phash(Image.open(ref_path).convert("L"))
            clip_hash = imagehash.phash(Image.open(frame_path).convert("L"))
            distance  = ref_hash - clip_hash
        except Exception as exc:  # noqa: BLE001
            LOG.warning("[verify] Hash comparison failed (%s) — skipping.", exc)
            return True

    passed = distance <= SIMILARITY_THRESHOLD
    status = "PASSED" if passed else f"FAILED (distance={distance}/{SIMILARITY_THRESHOLD})"
    LOG.info("[verify] %s → %s", species, status)
    print(f"[verify] {species}: {status}")

    # Write to verification.log in the project root
    log_file = Path(__file__).parent / "verification.log"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"{species}: {status}\n")

    return passed

