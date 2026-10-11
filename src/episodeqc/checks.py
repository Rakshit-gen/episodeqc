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
