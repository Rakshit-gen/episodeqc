"""Cross-check against pyloudnorm, an independent BS.1770 implementation."""

import numpy as np
import pytest
from helpers import noise

from episodeqc.analyze import analyze_array
from episodeqc.loudness import integrated

pyln = pytest.importorskip("pyloudnorm")


def program(rate, seed):
    """Noise bursts at different levels with gaps, a rough stand-in for speech."""
    rng = np.random.default_rng(seed)
    parts = []
    for _ in range(12):
        parts.append(
            noise(
                seconds=rng.uniform(0.5, 3),
                rate=rate,
                amp=rng.uniform(0.01, 0.3),
                seed=int(rng.integers(1 << 30)),
            )
        )
        parts.append(np.zeros((round(rng.uniform(0.1, 1.5) * rate), 2)))
    return np.concatenate(parts)


@pytest.mark.parametrize("rate", [44100, 48000])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_pyloudnorm(rate, seed):
    x = program(rate, seed)
    # Trim to whole 100 ms frames so both tools see the same samples.
    frame = round(rate * 0.1)
    x = x[: len(x) // frame * frame]
    ours = integrated(analyze_array(x, rate))
    theirs = pyln.Meter(rate).integrated_loudness(x)
    assert ours == pytest.approx(theirs, abs=0.05)
