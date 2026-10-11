"""Peak levels in dBFS / dBTP."""

import math

from .analyze import Frames


def db(linear: float) -> float:
    return 20 * math.log10(linear) if linear > 0 else float("-inf")


def sample_peak_db(fr: Frames) -> float:
    return db(fr.sample_peak)


def true_peak_db(fr: Frames) -> float:
    return db(fr.true_peak)
