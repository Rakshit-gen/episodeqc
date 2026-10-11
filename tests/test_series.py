from test_report import make

from episodeqc.series import check_series


def test_outlier_episode_is_flagged():
    # Every episode is inside the podcast tolerance, but ep3 stands out.
    reps = [make(f"ep{i}.wav", integrated=v) for i, v in enumerate([-16.2, -15.9, -16.0, -17.0])]
    assert check_series(reps, tolerance=0.8) == -16.1
    flagged = [r.path for r in reps if r.status == "warn"]
    assert flagged == ["ep3.wav"]
    assert "-0.9 LU" in reps[3].results[-1].message


def test_too_few_episodes():
    reps = [make("a.wav"), make("b.wav", integrated=-20.0)]
    assert check_series(reps) is None
    assert all(r.results[-1].check != "series" for r in reps)
