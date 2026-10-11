import numpy as np
import pytest

from episodeqc.analyze import analyze_array


def with_clips(spans, n=48000, channels=1):
    x = np.full((n, channels), 0.2)
    for start, length, ch in spans:
        x[start : start + length, ch] = 1.0
    return x


@pytest.mark.parametrize("chunk", [97, 1000, 100000])
def test_runs_are_found_whatever_the_chunking(chunk):
    x = with_clips([(100, 5, 0), (20000, 3, 0), (30000, 2, 0), (47990, 10, 0)])
    fr = analyze_array(x, 48000, chunk=chunk)
    assert fr.clips == [(100, 0, 5), (20000, 0, 3), (47990, 0, 10)]
    assert fr.clip_count == 3


def test_negative_full_scale_counts():
    x = with_clips([])
    x[500:510] = -1.0
    assert analyze_array(x, 48000).clip_count == 1


def test_channels_are_tracked_separately():
    x = with_clips([(100, 4, 0), (100, 4, 1)], channels=2)
    assert analyze_array(x, 48000, chunk=101).clips == [(100, 0, 4), (100, 1, 4)]


def test_a_single_loud_sample_is_not_a_clip():
    x = with_clips([(100, 1, 0), (200, 2, 0)])
    assert analyze_array(x, 48000).clip_count == 0
