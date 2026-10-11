import pytest
from test_checks import meas

from episodeqc.fix import suggest_gain
from episodeqc.profiles import BUILTIN, Profile


def test_on_target_needs_nothing():
    assert suggest_gain(meas(integrated=-16.3), BUILTIN["podcast"]) is None


def test_quiet_episode_gets_gain():
    fix = suggest_gain(meas(integrated=-20.0, true_peak=-6.0), BUILTIN["podcast"])
    assert fix.gain_db == pytest.approx(4.0)
    assert not fix.needs_limiter
    assert fix.describe() == "apply +4.0 dB"


def test_gain_that_would_clip_needs_a_limiter():
    fix = suggest_gain(meas(integrated=-22.0, true_peak=-3.0), BUILTIN["podcast"])
    assert fix.needs_limiter
    assert fix.peak_after == pytest.approx(3.0)
    assert "limiter" in fix.describe()


def test_acx_aims_for_the_middle_of_the_rms_window():
    fix = suggest_gain(meas(rms=-26.0, sample_peak=-12.0), BUILTIN["acx"])
    assert fix.gain_db == pytest.approx(5.5)
    assert not fix.needs_limiter


def test_no_level_spec():
    assert suggest_gain(meas(integrated=-30), Profile(name="bare")) is None
