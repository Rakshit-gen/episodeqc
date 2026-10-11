import pytest
import soundfile as sf
from test_cli import at_lufs, write

from episodeqc.analyze import analyze_file
from episodeqc.cli import main
from episodeqc.loudness import integrated


def test_quiet_episode_is_brought_to_target(tmp_path, capsys):
    src = (
        write(tmp_path / "in" / "ep.wav", at_lufs(-21.0))
        if (tmp_path / "in").mkdir() is None
        else None
    )
    assert main(["normalize", str(src), "-o", str(tmp_path / "out")]) == 0
    dst = tmp_path / "out" / "ep.wav"
    assert integrated(analyze_file(dst)) == pytest.approx(-16.0, abs=0.05)
    assert sf.info(dst).subtype == sf.info(src).subtype
    assert "apply +5.0 dB" in capsys.readouterr().out


def test_refuses_when_gain_would_clip(tmp_path, capsys):
    import numpy as np
    from helpers import sine

    # Quiet overall but with a loud spike: gain to -16 LUFS would push it past -1 dBTP.
    x = np.concatenate([sine(seconds=6, amp=0.02), sine(seconds=0.05, amp=0.9)])
    src = write(tmp_path / "ep.wav", x)
    assert main(["normalize", str(src), "-o", str(tmp_path / "out")]) == 1
    assert "needs a limiter" in capsys.readouterr().out
    assert not (tmp_path / "out" / "ep.wav").exists()


def test_will_not_overwrite_input(tmp_path, capsys):
    src = write(tmp_path / "ep.wav", at_lufs(-20.0))
    assert main(["normalize", str(src), "-o", str(tmp_path)]) == 2
