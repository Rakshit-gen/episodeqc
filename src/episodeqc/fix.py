"""How to fix a level problem: the gain to apply, and whether gain alone is enough."""

import math
from dataclasses import dataclass

from .measure import Measurements
from .profiles import Profile


@dataclass
class GainFix:
    gain_db: float
    peak_after: float  # dBTP (or dBFS for sample-peak specs) after the gain
    peak_limit: float | None
    needs_limiter: bool

    def describe(self) -> str:
        text = f"apply {self.gain_db:+.1f} dB"
        if self.needs_limiter:
            text += (
                f", but peaks would reach {self.peak_after:.1f} (max {self.peak_limit:g}),"
                " so it needs a limiter, not just gain"
            )
        return text


def suggest_gain(m: Measurements, p: Profile) -> GainFix | None:
    """Gain that puts the episode on target, or None when it already is (or is silent)."""
    if math.isinf(m.integrated):
        return None
    if p.loudness is not None:
        gain = p.loudness - m.integrated
        if abs(gain) <= p.loudness_tolerance:
            return None
    elif p.rms_min is not None and p.rms_max is not None:
        if p.rms_min <= m.rms <= p.rms_max:
            return None
        gain = (p.rms_min + p.rms_max) / 2 - m.rms
    else:
        return None

    if p.max_true_peak is not None:
        peak, limit = m.true_peak + gain, p.max_true_peak
    elif p.max_sample_peak is not None:
        peak, limit = m.sample_peak + gain, p.max_sample_peak
    else:
        peak, limit = m.true_peak + gain, None
    return GainFix(round(gain, 2), round(peak, 2), limit, limit is not None and peak > limit)
