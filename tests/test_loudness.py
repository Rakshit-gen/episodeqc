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
