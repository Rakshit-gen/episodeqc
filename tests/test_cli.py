import json

import numpy as np
import pytest
import soundfile as sf
from helpers import sine

from episodeqc.cli import main


def write(path, x, rate=48000):
    sf.write(path, x, rate, subtype="PCM_24")
    return path


def at_lufs(target, seconds=6.0):
    # A 1 kHz mono sine reads -3.01 LUFS at full scale.
    return sine(seconds=seconds, amp=10 ** ((target + 3.01) / 20))


def test_passing_episode_exits_0(tmp_path, capsys):
    ep = write(tmp_path / "ep.wav", at_lufs(-16.0))
    assert main(["check", str(ep)]) == 0
    assert "[PASS]" in capsys.readouterr().out


def test_failing_episode_exits_1(tmp_path, capsys):
    ep = write(tmp_path / "ep.wav", at_lufs(-24.0))
    assert main(["check", str(ep)]) == 1
    out = capsys.readouterr().out
    assert "FAIL  loudness" in out and "apply +8.0 dB" in out


def test_json(tmp_path, capsys):
    ep = write(tmp_path / "ep.wav", at_lufs(-23.0))
    assert main(["check", "-p", "ebu-r128", "-f", "json", str(ep)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["episodes"][0]["measurements"]["integrated"] == pytest.approx(-23.0, abs=0.05)


def test_unknown_profile_exits_2(tmp_path, capsys):
    ep = write(tmp_path / "ep.wav", at_lufs(-16.0))
    assert main(["check", "-p", "nope", str(ep)]) == 2
    assert "built-in" in capsys.readouterr().err


def test_profile_file(tmp_path):
    prof = tmp_path / "studio.toml"
    prof.write_text("loudness = -24.0\n")
    ep = write(tmp_path / "ep.wav", at_lufs(-24.0))
    assert main(["check", "-p", str(prof), str(ep)]) == 0


def test_not_audio_exits_2(tmp_path, capsys):
    bad = tmp_path / "notes.wav"
    bad.write_text("hello")
    assert main(["check", str(bad)]) == 2
    assert "notes.wav" in capsys.readouterr().err


def test_silent_file(tmp_path, capsys):
    ep = write(tmp_path / "ep.wav", np.zeros(48000 * 3))
    assert main(["check", str(ep)]) == 1
    assert "-inf LUFS" in capsys.readouterr().out


def test_folder_is_searched(tmp_path, capsys):
    season = tmp_path / "season1"
    (season / "part2").mkdir(parents=True)
    (season / ".trash").mkdir()
    write(season / "ep02.wav", at_lufs(-16.0))
    write(season / "part2" / "ep10.flac", at_lufs(-16.0))
    write(season / ".trash" / "old.wav", at_lufs(-30.0))
    (season / "cover.jpg").write_bytes(b"x")
    assert main(["check", str(season)]) == 0
    out = capsys.readouterr().out
    assert "ep02.wav" in out and "ep10.flac" in out and "old.wav" not in out
    assert "2 episodes" in out


def test_empty_folder_exits_2(tmp_path, capsys):
    assert main(["check", str(tmp_path)]) == 2
    assert "no audio files" in capsys.readouterr().err


def test_one_bad_file_does_not_stop_the_rest(tmp_path, capsys):
    write(tmp_path / "ep01.wav", at_lufs(-16.0))
    (tmp_path / "ep02.wav").write_text("broken upload")
    write(tmp_path / "ep03.wav", at_lufs(-16.0))
    assert main(["check", str(tmp_path)]) == 2
    out = capsys.readouterr()
    assert "ep01.wav" in out.out and "ep03.wav" in out.out
    assert "ep02.wav" in out.err


def test_strict_fails_on_warnings(tmp_path):
    stereo = np.repeat(at_lufs(-19.0)[:, :1], 2, axis=1)  # identical channels: a warning
    ep = write(tmp_path / "ep.wav", stereo)
    assert main(["check", str(ep)]) == 0
    assert main(["check", "--strict", str(ep)]) == 1


def test_season_outlier(tmp_path, capsys):
    for i, lufs in enumerate([-16.0, -16.2, -15.8, -16.9]):
        write(tmp_path / f"ep{i}.wav", at_lufs(lufs))
    assert main(["check", "--series-tolerance", "0.5", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "warn  series: -0.8 LU" in out
    assert main(["check", "--no-series", str(tmp_path)]) == 0
    assert "series" not in capsys.readouterr().out


def test_jobs_give_the_same_report(tmp_path, capsys):
    for i, lufs in enumerate([-16.0, -22.0, -16.4]):
        write(tmp_path / f"ep{i}.wav", at_lufs(lufs, seconds=3))
    (tmp_path / "ep9.wav").write_text("broken")
    assert main(["check", str(tmp_path)]) == 2
    one = capsys.readouterr()
    assert main(["check", "-j", "2", str(tmp_path)]) == 2
    two = capsys.readouterr()
    assert one.out == two.out
    assert "ep9.wav" in two.err
