"""Everything we know about one episode, in one place."""

import math
from dataclasses import asdict, dataclass

from . import levels, loudness, peaks
from .analyze import Frames
from .silence import SILENCE_DB, find_silence


@dataclass
class Measurements:
    duration: float
    rate: int
    channels: int
    integrated: float  # LUFS
    lra: float  # LU
    momentary_max: float  # LUFS
    short_term_max: float  # LUFS
    true_peak: float  # dBTP
    sample_peak: float  # dBFS
    rms: float  # dBFS
    noise_floor: float  # dBFS
    dc_offset: float  # fraction of full scale
    clip_count: int
    clips: list  # first clip events as (seconds, channel, samples)
    dual_mono: bool
    lead_silence: float  # s
    tail_silence: float  # s
    gaps: list  # (start s, length s) of silences in the middle

    def to_dict(self) -> dict:
        d = asdict(self)
        # JSON has no infinity; silence reads as null.
        return {k: (None if isinstance(v, float) and math.isinf(v) else v) for k, v in d.items()}


def measure(fr: Frames, silence_db: float = SILENCE_DB, min_gap: float = 0.0) -> Measurements:
    s = find_silence(fr, threshold_db=silence_db, min_gap=min_gap)
    return Measurements(
        duration=round(fr.duration, 3),
        rate=fr.rate,
        channels=fr.channels,
        integrated=loudness.integrated(fr),
        lra=loudness.loudness_range(fr),
        momentary_max=loudness.momentary_max(fr),
        short_term_max=loudness.short_term_max(fr),
        true_peak=peaks.true_peak_db(fr),
        sample_peak=peaks.sample_peak_db(fr),
        rms=levels.rms_db(fr),
        noise_floor=levels.noise_floor_db(fr),
        dc_offset=levels.dc_offset(fr),
        clip_count=fr.clip_count,
        clips=[(round(start / fr.rate, 3), ch, n) for start, ch, n in fr.clips[:20]],
        dual_mono=fr.dual_mono,
        lead_silence=s.lead,
        tail_silence=s.tail,
        gaps=s.gaps,
    )
