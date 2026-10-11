"""Delivery specs. A profile says what a finished episode must look like.

Every limit is optional; a profile only checks what it sets.
"""

from dataclasses import dataclass, field, fields


@dataclass(frozen=True)
class Profile:
    name: str
    description: str = ""
    loudness: float | None = None  # integrated target, LUFS
    loudness_tolerance: float = 1.0  # LU either side of the target
    max_true_peak: float | None = None  # dBTP
    max_sample_peak: float | None = None  # dBFS
    max_lra: float | None = None  # LU
    rms_min: float | None = None  # dBFS
    rms_max: float | None = None  # dBFS
    max_noise_floor: float | None = None  # dBFS
    lead_silence: tuple[float, float] | None = None  # (min, max) seconds
    tail_silence: tuple[float, float] | None = None  # (min, max) seconds
    max_gap: float | None = None  # longest dead air allowed mid-episode, seconds
    silence_db: float = -50.0  # below this a 100 ms frame counts as silent
    sample_rates: tuple[int, ...] = ()
    channels: tuple[int, ...] = ()
    min_duration: float | None = None  # seconds
    max_duration: float | None = None  # seconds
    max_dc_offset: float = 0.01  # fraction of full scale
    max_clips: int = 0
    warn_dual_mono: bool = True
    disabled: frozenset[str] = field(default_factory=frozenset)


BUILTIN = {
    p.name: p
    for p in [
        Profile(
            name="ebu-r128",
            description="Broadcast: -23 LUFS, true peak at most -1 dBTP (EBU R128).",
            loudness=-23.0,
            loudness_tolerance=0.5,
            max_true_peak=-1.0,
        ),
        Profile(
            name="podcast",
            description="Spoken word for phones: -16 LUFS, true peak at most -1 dBTP.",
            loudness=-16.0,
            max_true_peak=-1.0,
            max_lra=15.0,
            lead_silence=(0.0, 2.0),
            tail_silence=(0.0, 5.0),
            max_gap=5.0,
        ),
        Profile(
            name="acx",
            description="Audiobooks (ACX): RMS -23 to -18 dB, peaks below -3 dB, "
            "noise floor below -60 dB, 0.5-1 s room tone at the head, 1-5 s at the tail.",
            rms_min=-23.0,
            rms_max=-18.0,
            max_sample_peak=-3.0,
            max_noise_floor=-60.0,
            lead_silence=(0.5, 1.0),
            tail_silence=(1.0, 5.0),
            sample_rates=(44100,),
            max_duration=120 * 60,
            silence_db=-55.0,
        ),
    ]
}

FIELDS = {f.name for f in fields(Profile)}
