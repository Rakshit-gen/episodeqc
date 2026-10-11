import numpy as np
import pytest
from helpers import noise, sine

from episodeqc.analyze import analyze_array
from episodeqc.levels import noise_floor_db, rms_db


def test_rms_of_full_scale_sine():
    assert rms_db(analyze_array(sine(seconds=2), 48000)) == pytest.approx(-3.01, abs=0.01)


def test_noise_floor_is_the_quiet_gap():
    speech = sine(seconds=5, amp=0.3)
    room = noise(seconds=1, amp=10 ** (-65 / 20), channels=1)
    fr = analyze_array(np.concatenate([speech, room, speech]), 48000)
    assert noise_floor_db(fr) == pytest.approx(-65, abs=0.5)


def test_digital_silence_is_not_the_noise_floor():
    speech = sine(seconds=5, amp=0.3)
    room = noise(seconds=1, amp=10 ** (-62 / 20), channels=1)
    gap = np.zeros((48000, 1))
    fr = analyze_array(np.concatenate([speech, gap, room, speech]), 48000)
    assert noise_floor_db(fr) == pytest.approx(-62, abs=0.5)


def test_dc_offset():
    from episodeqc.levels import dc_offset

    x = sine(seconds=2, amp=0.3, channels=2)
    x[:, 1] += 0.02
    assert dc_offset(analyze_array(x, 48000)) == pytest.approx(0.02, abs=1e-4)
    assert dc_offset(analyze_array(sine(seconds=2), 48000)) < 1e-6
