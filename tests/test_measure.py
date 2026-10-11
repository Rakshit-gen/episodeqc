import json

import numpy as np
import pytest
from helpers import sine

from episodeqc.analyze import analyze_array
from episodeqc.measure import measure


def test_measure_collects_everything():
    x = np.concatenate([np.zeros((48000, 2)), sine(seconds=5, amp=0.5, channels=2)])
    m = measure(analyze_array(x, 48000))
    assert m.duration == pytest.approx(6.0)
    assert m.channels == 2
    assert m.lead_silence == pytest.approx(1.0)
    assert m.dual_mono
    assert m.true_peak == pytest.approx(-6.02, abs=0.05)


def test_to_dict_is_json_safe():
    m = measure(analyze_array(np.zeros((48000, 1)), 48000))
    d = m.to_dict()
    assert d["integrated"] is None
    json.dumps(d)
