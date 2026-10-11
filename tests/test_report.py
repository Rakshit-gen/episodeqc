from test_checks import meas

from episodeqc.checks import run_checks
from episodeqc.fix import suggest_gain
from episodeqc.profiles import BUILTIN
from episodeqc.report import EpisodeReport, text


def make(path, **kw):
    m = meas(**kw)
    p = BUILTIN["podcast"]
    return EpisodeReport(path, m, run_checks(m, p), suggest_gain(m, p))


def test_text_shows_problems_and_fix():
    out = text([make("ep01.wav"), make("ep02.wav", integrated=-21.0, true_peak=-8.0)])
    assert "ep01.wav  [PASS]" in out
    assert "ep02.wav  [FAIL]" in out
    assert "FAIL  loudness" in out
    assert "fix   apply +5.0 dB" in out
    assert out.endswith("2 episodes: 1 passed, 0 with warnings, 1 failed")


def test_passing_checks_only_in_verbose():
    rep = [make("ep01.wav")]
    assert "ok    loudness" not in text(rep)
    assert "ok    loudness" in text(rep, verbose=True)


def test_json_round_trips():
    import json

    from episodeqc.report import as_json

    data = json.loads(as_json([make("a.wav", integrated=-21.0, true_peak=-8.0)], "podcast"))
    ep = data["episodes"][0]
    assert data["profile"] == "podcast"
    assert ep["status"] == "fail"
    assert ep["fix"]["gain_db"] == 5.0
    assert {c["check"] for c in ep["checks"]} >= {"loudness", "true-peak"}


def test_github_annotations():
    from episodeqc.report import github

    out = github([make("s1/ep, 2.wav", integrated=-21.0, true_peak=-8.0, dual_mono=True)])
    lines = out.splitlines()
    assert lines[0].startswith("::error file=s1/ep%2C 2.wav,title=episodeqc loudness::")
    assert "apply +5.0 dB" in lines[0]
    assert any(line.startswith("::warning ") and "dual-mono" in line for line in lines)
