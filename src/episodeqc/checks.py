"""Checks compare measurements with a profile and say pass, warn or fail."""

import math
from collections.abc import Callable
from dataclasses import dataclass

from .measure import Measurements
from .profiles import Profile

PASS, WARN, FAIL = "pass", "warn", "fail"


@dataclass
class Result:
    check: str
    status: str
    message: str


CHECKS: dict[str, Callable[[Measurements, Profile], Result | None]] = {}


def check(name: str):
    def register(fn):
        CHECKS[name] = fn
        return fn

    return register


def fmt(x: float, unit: str) -> str:
    return f"-inf {unit}" if math.isinf(x) else f"{x:.1f} {unit}"


@check("loudness")
def _loudness(m: Measurements, p: Profile) -> Result | None:
    if p.loudness is None:
        return None
    off = m.integrated - p.loudness
    msg = (
        f"integrated {fmt(m.integrated, 'LUFS')}, target {p.loudness:.1f} ± {p.loudness_tolerance}"
    )
    if math.isinf(off) or abs(off) > p.loudness_tolerance:
        return Result("loudness", FAIL, msg)
    return Result("loudness", PASS, msg)


@check("true-peak")
def _true_peak(m: Measurements, p: Profile) -> Result | None:
    if p.max_true_peak is None:
        return None
    msg = f"true peak {fmt(m.true_peak, 'dBTP')}, max {p.max_true_peak:.1f}"
    return Result("true-peak", FAIL if m.true_peak > p.max_true_peak else PASS, msg)


@check("sample-peak")
def _sample_peak(m: Measurements, p: Profile) -> Result | None:
    if p.max_sample_peak is None:
        return None
    msg = f"peak {fmt(m.sample_peak, 'dBFS')}, max {p.max_sample_peak:.1f}"
    return Result("sample-peak", FAIL if m.sample_peak > p.max_sample_peak else PASS, msg)


@check("loudness-range")
def _lra(m: Measurements, p: Profile) -> Result | None:
    if p.max_lra is None:
        return None
    # A wide range is a mix decision, not a broken file, so this only warns:
    # whispers that vanish on a phone speaker, or shouting that makes people
    # reach for the volume.
    msg = f"loudness range {m.lra:.1f} LU, max {p.max_lra:.1f}"
    return Result("loudness-range", WARN if m.lra > p.max_lra else PASS, msg)


def _range(name: str, label: str, value: float, limits) -> Result | None:
    if limits is None:
        return None
    lo, hi = limits
    msg = f"{label} {value:.2f} s, allowed {lo:g}-{hi:g} s"
    return Result(name, PASS if lo <= value <= hi else FAIL, msg)


@check("lead-silence")
def _lead(m: Measurements, p: Profile) -> Result | None:
    return _range("lead-silence", "silence at the start", m.lead_silence, p.lead_silence)


@check("tail-silence")
def _tail(m: Measurements, p: Profile) -> Result | None:
    return _range("tail-silence", "silence at the end", m.tail_silence, p.tail_silence)


@check("dead-air")
def _gaps(m: Measurements, p: Profile) -> Result | None:
    if p.max_gap is None:
        return None
    long = [(start, length) for start, length in m.gaps if length > p.max_gap]
    if not long:
        return Result("dead-air", PASS, f"no silence longer than {p.max_gap:g} s")
    where = ", ".join(f"{length:.1f} s at {clock(start)}" for start, length in long[:5])
    more = f" and {len(long) - 5} more" if len(long) > 5 else ""
    return Result("dead-air", FAIL, f"{len(long)} silences over {p.max_gap:g} s: {where}{more}")


@check("rms")
def _rms(m: Measurements, p: Profile) -> Result | None:
    if p.rms_min is None and p.rms_max is None:
        return None
    lo = -math.inf if p.rms_min is None else p.rms_min
    hi = math.inf if p.rms_max is None else p.rms_max
    msg = f"RMS {fmt(m.rms, 'dBFS')}, allowed {lo:g} to {hi:g}"
    return Result("rms", PASS if lo <= m.rms <= hi else FAIL, msg)


@check("noise-floor")
def _noise(m: Measurements, p: Profile) -> Result | None:
    if p.max_noise_floor is None:
        return None
    msg = f"noise floor {fmt(m.noise_floor, 'dBFS')}, max {p.max_noise_floor:g}"
    return Result("noise-floor", FAIL if m.noise_floor > p.max_noise_floor else PASS, msg)


@check("clipping")
def _clipping(m: Measurements, p: Profile) -> Result | None:
    if m.clip_count <= p.max_clips:
        return Result("clipping", PASS, f"{m.clip_count} clipped runs")
    where = ", ".join(clock(t) for t, _, _ in m.clips[:5])
    return Result("clipping", FAIL, f"{m.clip_count} clipped runs, first at {where}")


@check("dc-offset")
def _dc(m: Measurements, p: Profile) -> Result | None:
    msg = f"DC offset {m.dc_offset * 100:.2f}% of full scale"
    return Result("dc-offset", WARN if m.dc_offset > p.max_dc_offset else PASS, msg)


@check("dual-mono")
def _dual_mono(m: Measurements, p: Profile) -> Result | None:
    if not p.warn_dual_mono or m.channels != 2:
        return None
    if m.dual_mono:
        return Result(
            "dual-mono", WARN, "both channels are identical; a mono file is half the size"
        )
    return Result("dual-mono", PASS, "channels differ")


@check("format")
def _format(m: Measurements, p: Profile) -> Result | None:
    problems = []
    if p.sample_rates and m.rate not in p.sample_rates:
        problems.append(f"sample rate {m.rate} Hz not in {', '.join(map(str, p.sample_rates))}")
    if p.channels and m.channels not in p.channels:
        problems.append(f"{m.channels} channels, expected {' or '.join(map(str, p.channels))}")
    if not (p.sample_rates or p.channels):
        return None
    if problems:
        return Result("format", FAIL, "; ".join(problems))
    return Result("format", PASS, f"{m.rate} Hz, {m.channels} ch")


@check("duration")
def _duration(m: Measurements, p: Profile) -> Result | None:
    if p.min_duration is None and p.max_duration is None:
        return None
    msg = f"length {clock(m.duration)}"
    if p.min_duration is not None and m.duration < p.min_duration:
        return Result("duration", FAIL, f"{msg}, shorter than {clock(p.min_duration)}")
    if p.max_duration is not None and m.duration > p.max_duration:
        return Result("duration", FAIL, f"{msg}, longer than {clock(p.max_duration)}")
    return Result("duration", PASS, msg)


def clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def run_checks(m: Measurements, p: Profile) -> list[Result]:
    results = []
    for name, fn in CHECKS.items():
        if name in p.disabled:
            continue
        r = fn(m, p)
        if r is not None:
            results.append(r)
    return results


def worst(results: list[Result]) -> str:
    statuses = {r.status for r in results}
    return FAIL if FAIL in statuses else WARN if WARN in statuses else PASS
