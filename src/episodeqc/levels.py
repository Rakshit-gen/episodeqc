"""Unweighted levels: RMS and noise floor, as audiobook specs like ACX define them."""

import math

import numpy as np

from .analyze import Frames

NOISE_WINDOW_FRAMES = 5  # 500 ms


def _db(power: float) -> float:
    return 10 * math.log10(power) if power > 0 else float("-inf")


def rms_db(fr: Frames) -> float:
    """RMS level of the whole file in dBFS, averaged over channels."""
    if not len(fr.power):
        return float("-inf")
    return _db(float(fr.power.mean()))


def window_rms_db(fr: Frames, frames: int) -> np.ndarray:
    """RMS in dBFS of every sliding window of `frames` frames."""
    p = fr.power.mean(axis=1)
    if len(p) < frames:
        return np.zeros(0)
    c = np.concatenate([[0.0], np.cumsum(p)])
    win = (c[frames:] - c[:-frames]) / frames
    with np.errstate(divide="ignore"):
        return 10 * np.log10(win)


def noise_floor_db(fr: Frames) -> float:
    """Level of the quietest half second: the room tone between lines.

    Digital silence (an all-zero window) is skipped, since that is an edit,
    not the noise floor of the recording.
    """
    w = window_rms_db(fr, NOISE_WINDOW_FRAMES)
    if not len(w):
        return float("-inf")
    silent = np.concatenate([[0], np.cumsum(fr.power.mean(axis=1) == 0)])
    touches_silence = (silent[NOISE_WINDOW_FRAMES:] - silent[:-NOISE_WINDOW_FRAMES]) > 0
    w = w[~touches_silence]
    return float(w.min()) if len(w) else float("-inf")
