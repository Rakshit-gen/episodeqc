"""Silence: dead air at the start, at the end, and in the middle of an episode."""

from dataclasses import dataclass

import numpy as np

from .analyze import FRAME_SECONDS, Frames

SILENCE_DB = -50.0


@dataclass
class Silence:
    lead: float  # seconds of silence before the first sound
    tail: float  # seconds of silence after the last sound
    gaps: list[tuple[float, float]]  # (start, length) of silences in the middle


def frame_db(fr: Frames) -> np.ndarray:
    p = fr.power.mean(axis=1)
    with np.errstate(divide="ignore"):
        return 10 * np.log10(p)


def find_silence(fr: Frames, threshold_db: float = SILENCE_DB, min_gap: float = 0.0) -> Silence:
    quiet = frame_db(fr) < threshold_db
    n = len(quiet)
    if not n or quiet.all():
        return Silence(lead=fr.duration, tail=0.0, gaps=[])

    edges = np.diff(np.concatenate([[0], quiet.astype(np.int8), [0]]))
    runs = list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True))
    lead = tail = 0.0
    gaps = []
    for a, b in runs:
        length = (b - a) * FRAME_SECONDS
        if a == 0:
            lead = length
        elif b == n:
            # The partial frame after the last whole one belongs to the tail.
            tail = fr.duration - a * FRAME_SECONDS
        elif length >= min_gap:
            gaps.append((round(a * FRAME_SECONDS, 3), round(length, 3)))
    return Silence(lead=round(lead, 3), tail=round(tail, 3), gaps=gaps)
