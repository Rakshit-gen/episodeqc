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
