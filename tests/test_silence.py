import numpy as np
import pytest
from helpers import sine

from episodeqc.analyze import analyze_array
from episodeqc.silence import find_silence


def quiet(seconds):
    return np.zeros((round(seconds * 48000), 1))


def test_lead_tail_and_gaps():
    x = np.concatenate(
        [
            quiet(1.5),
            sine(seconds=3, amp=0.3),
            quiet(4),
            sine(seconds=2, amp=0.3),
            quiet(0.3),
            sine(seconds=1, amp=0.3),
            quiet(2.25),
        ]
    )
    s = find_silence(analyze_array(x, 48000), min_gap=1.0)
    assert s.lead == pytest.approx(1.5)
    assert s.tail == pytest.approx(2.25)
    assert s.gaps == [(4.5, 4.0)]


def test_no_silence():
    s = find_silence(analyze_array(sine(seconds=2, amp=0.3), 48000))
    assert (s.lead, s.tail, s.gaps) == (0.0, 0.0, [])


def test_all_silent():
    s = find_silence(analyze_array(quiet(3), 48000))
    assert s.lead == pytest.approx(3.0)


def test_threshold_decides_what_counts():
    hum = sine(seconds=2, amp=10 ** (-45 / 20) * 2**0.5)  # -45 dBFS RMS
    x = np.concatenate([sine(seconds=1, amp=0.3), hum, sine(seconds=1, amp=0.3)])
    fr = analyze_array(x, 48000)
    assert find_silence(fr, threshold_db=-50).gaps == []
    assert find_silence(fr, threshold_db=-40).gaps == [(1.0, 2.0)]
