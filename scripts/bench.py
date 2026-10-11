"""Time a check of one synthetic episode and report peak memory.

    uv run python scripts/bench.py [minutes]

Writes a temporary stereo 48 kHz 16-bit WAV of speech-like noise bursts,
then runs the full analysis on it. The file is deleted afterwards.
"""

import resource
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from episodeqc.analyze import analyze_file
from episodeqc.checks import run_checks
from episodeqc.measure import measure
from episodeqc.profiles import BUILTIN

RATE = 48000


def write_episode(path: Path, minutes: float) -> None:
    rng = np.random.default_rng(0)
    with sf.SoundFile(str(path), "w", RATE, 2, subtype="PCM_16") as f:
        for _ in range(int(minutes * 60)):
            level = rng.uniform(0.02, 0.2) if rng.random() > 0.15 else 0.0
            f.write(level * rng.standard_normal((RATE, 2)))


def main() -> None:
    minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 10
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "episode.wav"
        write_episode(path, minutes)
        size = path.stat().st_size / 1e6
        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        times = []
        for _ in range(3):
            t = time.perf_counter()
            run_checks(measure(analyze_file(path)), BUILTIN["podcast"])
            times.append(time.perf_counter() - t)
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    scale = 1 if sys.platform == "darwin" else 1024  # bytes on macOS, KiB on Linux
    best = min(times)
    print(
        f"{minutes:g} min stereo 48 kHz ({size:.0f} MB): best of 3 {best:.2f} s, "
        f"{minutes * 60 / best:.0f}x real time"
    )
    print(f"peak RSS {peak * scale / 1e6:.0f} MB (before analysis {before * scale / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
