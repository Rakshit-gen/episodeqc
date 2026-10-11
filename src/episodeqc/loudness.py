"""Loudness from 100 ms power frames: BS.1770 integrated loudness with gating."""

import numpy as np

from .analyze import Frames

ABS_GATE = -70.0
REL_GATE = -10.0
BLOCK_FRAMES = 4  # 400 ms gating blocks, 75% overlap with 100 ms frames


def channel_weights(channels: int) -> np.ndarray:
    """BS.1770 channel weights. Surrounds in a 5.1 layout count 1.41x."""
    w = np.ones(channels)
    if channels == 6:  # L R C LFE Ls Rs
        w[3] = 0.0
        w[4:] = 1.41
    return w


def to_lufs(power) -> np.ndarray:
    power = np.asarray(power, dtype=np.float64)
    with np.errstate(divide="ignore"):
        return -0.691 + 10 * np.log10(power)


def block_power(fr: Frames, frames_per_block: int) -> np.ndarray:
    """Channel-weighted mean square of each sliding block of whole frames."""
    weighted = fr.kpower @ channel_weights(fr.channels)
    if len(weighted) < frames_per_block:
        return np.zeros(0)
    c = np.concatenate([[0.0], np.cumsum(weighted)])
    return (c[frames_per_block:] - c[:-frames_per_block]) / frames_per_block


def integrated(fr: Frames) -> float:
    """Gated integrated loudness in LUFS, or -inf for silence."""
    blocks = block_power(fr, BLOCK_FRAMES)
    blocks = blocks[to_lufs(blocks) > ABS_GATE]
    if not len(blocks):
        return float("-inf")
    threshold = to_lufs(blocks.mean()) + REL_GATE
    gated = blocks[to_lufs(blocks) > threshold]
    return float(to_lufs(gated.mean()))
