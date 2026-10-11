"""Apply the suggested gain. Plain gain only: if the target needs a limiter,
we say so and leave the file alone rather than clip it."""

from pathlib import Path

import soundfile as sf

from .analyze import analyze_file
from .fix import GainFix, suggest_gain
from .measure import measure
from .profiles import Profile


class NeedsLimiter(Exception):
    pass


def apply_gain(src: Path, dst: Path, gain_db: float, chunk_seconds: float = 10.0) -> None:
    factor = 10 ** (gain_db / 20)
    with sf.SoundFile(str(src)) as f:
        info = dict(
            samplerate=f.samplerate, channels=f.channels, format=f.format, subtype=f.subtype
        )
        dst.parent.mkdir(parents=True, exist_ok=True)
        with sf.SoundFile(str(dst), "w", **info) as out:
            for chunk in f.blocks(
                blocksize=int(chunk_seconds * f.samplerate), dtype="float64", always_2d=True
            ):
                out.write(chunk * factor)


def normalize(src: Path, dst: Path, profile: Profile) -> GainFix | None:
    """Write a level-corrected copy of src to dst. Returns the fix applied, or
    None if src was already on target (dst is still written, unchanged)."""
    fix = suggest_gain(measure(analyze_file(src)), profile)
    if fix and fix.needs_limiter:
        raise NeedsLimiter(fix.describe())
    apply_gain(src, dst, fix.gain_db if fix else 0.0)
    return fix
