import numpy as np
import pytest
import soundfile as sf
from helpers import sine

from episodeqc.analyze import analyze_array, analyze_file


@pytest.mark.parametrize("fmt,subtype", [("WAV", "PCM_16"), ("WAV", "FLOAT"), ("FLAC", "PCM_24")])
def test_file_matches_array(tmp_path, fmt, subtype):
    x = sine(seconds=3, amp=0.5, channels=2, rate=44100)
    path = tmp_path / f"ep.{fmt.lower()}"
    sf.write(path, x, 44100, format=fmt, subtype=subtype)
    a = analyze_file(path, chunk_seconds=0.7)
    b = analyze_array(sf.read(path, always_2d=True)[0], 44100)
    assert (a.rate, a.channels, a.samples) == (44100, 2, len(x))
    np.testing.assert_allclose(a.kpower, b.kpower, rtol=1e-9)
    assert a.true_peak == pytest.approx(b.true_peak)


def test_missing_file(tmp_path):
    with pytest.raises(sf.LibsndfileError):
        analyze_file(tmp_path / "nope.wav")
