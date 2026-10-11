import numpy as np
import pytest
from helpers import sine

from episodeqc.analyze import analyze_array


def test_frames_are_100ms():
    fr = analyze_array(sine(seconds=2.05), 48000)
    assert fr.frame_len == 4800
    assert fr.kpower.shape == (20, 1)
    assert fr.duration == pytest.approx(2.05)


def test_chunk_size_does_not_change_result():
    x = sine(seconds=3, channels=2)
    a = analyze_array(x, 48000, chunk=1000)
    b = analyze_array(x, 48000, chunk=77777)
    np.testing.assert_allclose(a.kpower, b.kpower, rtol=1e-9)
    np.testing.assert_allclose(a.power, b.power, rtol=1e-12)


def test_plain_power_of_full_scale_sine_is_half():
    fr = analyze_array(sine(seconds=1), 48000)
    np.testing.assert_allclose(fr.power[2:], 0.5, rtol=1e-3)


def test_dual_mono():
    assert analyze_array(sine(seconds=1, channels=2), 48000).dual_mono
    x = sine(seconds=1, channels=2)
    x[24012, 1] = 0.0  # a sample that is not already zero
    assert not analyze_array(x, 48000).dual_mono
    assert not analyze_array(sine(seconds=1, channels=1), 48000).dual_mono
