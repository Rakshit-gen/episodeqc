import numpy as np
import pytest
from helpers import sine

from episodeqc.analyze import analyze_array
from episodeqc.peaks import sample_peak_db, true_peak_db


def test_intersample_peak_is_caught():
    # A sine at a quarter of the sample rate, phase-shifted 45 degrees, never
    # lands a sample on its crest: every sample is at 0.707 but the wave hits 1.0.
    x = sine(freq=12000, seconds=2, phase=np.pi / 4)
    fr = analyze_array(x, 48000)
    assert sample_peak_db(fr) == pytest.approx(-3.01, abs=0.01)
    assert true_peak_db(fr) == pytest.approx(0.0, abs=0.2)


def test_low_frequency_true_peak_equals_sample_peak():
    fr = analyze_array(sine(freq=100, seconds=2, amp=0.5), 48000)
    assert true_peak_db(fr) == pytest.approx(sample_peak_db(fr), abs=0.05)


def test_chunking_does_not_change_true_peak():
    x = sine(freq=12000, seconds=1, phase=np.pi / 4) * np.linspace(0.2, 1, 48000)[:, None]
    a = analyze_array(x, 48000, chunk=5)
    b = analyze_array(x, 48000, chunk=100000)
    assert a.true_peak == pytest.approx(b.true_peak, rel=1e-9)


def test_silence():
    fr = analyze_array(np.zeros((48000, 2)), 48000)
    assert true_peak_db(fr) == float("-inf")
