import math

import pytest
from helpers import noise, sine

from episodeqc.analyze import analyze_array
from episodeqc.loudness import integrated


def lufs(x, rate=48000):
    return integrated(analyze_array(x, rate))


def test_full_scale_1k_sine_reads_minus_3_01():
    # BS.1770: a 0 dBFS 1 kHz sine in one front channel reads -3.01 LKFS.
    assert lufs(sine(seconds=10)) == pytest.approx(-3.01, abs=0.01)


def test_level_tracks_gain():
    loud = lufs(sine(seconds=10, amp=1.0))
    quiet = lufs(sine(seconds=10, amp=0.1))
    assert loud - quiet == pytest.approx(20.0, abs=0.01)


def test_two_channels_are_summed():
    mono = lufs(sine(seconds=10, channels=1))
    stereo = lufs(sine(seconds=10, channels=2))
    assert stereo - mono == pytest.approx(3.01, abs=0.01)


def test_44k_matches_48k():
    assert lufs(sine(seconds=10, rate=44100), 44100) == pytest.approx(-3.01, abs=0.02)


def test_silence_is_minus_inf():
    assert lufs(sine(seconds=5, amp=0.0)) == -math.inf


def test_relative_gate_ignores_quiet_tail():
    import numpy as np

    speech = noise(seconds=10, amp=0.1)
    hiss = noise(seconds=10, amp=0.001, seed=1)
    alone = lufs(speech)
    with_tail = lufs(np.concatenate([speech, hiss]))
    assert with_tail == pytest.approx(alone, abs=0.1)


def test_momentary_catches_a_short_burst_that_short_term_smooths():
    import numpy as np

    from episodeqc.loudness import momentary_max, short_term_max

    bed = sine(seconds=10, amp=0.05)
    burst = sine(seconds=0.5, amp=0.5)
    fr = analyze_array(np.concatenate([bed, burst, bed]), 48000)
    assert momentary_max(fr) == pytest.approx(-3.01 - 6.02, abs=0.2)
    assert short_term_max(fr) < momentary_max(fr) - 6


def test_steady_tone_has_no_range():
    from episodeqc.loudness import loudness_range

    assert loudness_range(analyze_array(sine(seconds=20), 48000)) == pytest.approx(0, abs=0.01)


def test_range_of_two_levels():
    import numpy as np

    from episodeqc.loudness import loudness_range

    # Long stretches at two levels 10 dB apart give an LRA close to 10 LU.
    x = np.concatenate([sine(seconds=30, amp=0.3), sine(seconds=30, amp=0.3 / 10**0.5)])
    assert loudness_range(analyze_array(x, 48000)) == pytest.approx(10, abs=0.3)


def test_range_ignores_material_far_below_the_mean():
    import numpy as np

    from episodeqc.loudness import loudness_range

    x = np.concatenate([sine(seconds=30, amp=0.3), sine(seconds=30, amp=0.3 / 1000)])
    assert loudness_range(analyze_array(x, 48000)) < 1
