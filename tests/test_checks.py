from dataclasses import replace

import pytest

from episodeqc.checks import FAIL, PASS, WARN, run_checks, worst
from episodeqc.measure import Measurements
from episodeqc.profiles import Profile


def meas(**kw):
    base = dict(
        duration=600.0,
        rate=48000,
        channels=2,
        integrated=-16.0,
        lra=6.0,
        momentary_max=-8.0,
        short_term_max=-11.0,
        true_peak=-2.0,
        sample_peak=-2.3,
        rms=-19.0,
        noise_floor=-70.0,
        dc_offset=0.0,
        clip_count=0,
        clips=[],
        dual_mono=False,
        lead_silence=0.5,
        tail_silence=2.0,
        gaps=[],
    )
    base.update(kw)
    return Measurements(**base)


def status(m, p, name):
    return {r.check: r.status for r in run_checks(m, p)}.get(name)


P = Profile(name="t", loudness=-16.0, loudness_tolerance=1.0)


@pytest.mark.parametrize(
    "lufs,expected",
    [(-16.0, PASS), (-16.9, PASS), (-17.2, FAIL), (-14.5, FAIL), (float("-inf"), FAIL)],
)
def test_loudness(lufs, expected):
    assert status(meas(integrated=lufs), P, "loudness") == expected


def test_unset_limit_is_not_checked():
    assert status(meas(), Profile(name="bare"), "loudness") is None


def test_disabled():
    assert (
        status(meas(integrated=-30), replace(P, disabled=frozenset({"loudness"})), "loudness")
        is None
    )


def test_worst():
    from episodeqc.checks import Result

    assert worst([Result("a", PASS, ""), Result("b", WARN, "")]) == WARN
    assert worst([Result("a", FAIL, ""), Result("b", WARN, "")]) == FAIL
    assert worst([]) == PASS


def test_true_peak():
    p = Profile(name="t", max_true_peak=-1.0)
    assert status(meas(true_peak=-1.0), p, "true-peak") == PASS
    assert status(meas(true_peak=-0.4), p, "true-peak") == FAIL


def test_sample_peak():
    p = Profile(name="t", max_sample_peak=-3.0)
    assert status(meas(sample_peak=-3.5), p, "sample-peak") == PASS
    assert status(meas(sample_peak=-2.9), p, "sample-peak") == FAIL


def test_lra_only_warns():
    p = Profile(name="t", max_lra=15.0)
    assert status(meas(lra=9.0), p, "loudness-range") == PASS
    assert status(meas(lra=19.0), p, "loudness-range") == WARN
