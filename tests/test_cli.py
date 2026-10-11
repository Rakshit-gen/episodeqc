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
