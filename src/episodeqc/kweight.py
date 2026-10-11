"""K-weighting filter from ITU-R BS.1770.

The coefficients are derived from the analog prototype for any sample rate,
the same way libebur128 does it, so 44.1 kHz and 22.05 kHz files are measured
with the right filter instead of the 48 kHz table.
"""

from math import pi, tan

import numpy as np


def k_weighting_sos(rate: int) -> np.ndarray:
    """Return the two K-weighting biquads as a scipy-style SOS array (2, 6)."""
    # Stage 1: high shelf modelling the head.
    gain_db = 3.999843853973347
    f0 = 1681.974450955533
    q = 0.7071752369554196
    k = tan(pi * f0 / rate)
    vh = 10 ** (gain_db / 20)
    vb = vh**0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf = [
        (vh + vb * k / q + k * k) / a0,
        2 * (k * k - vh) / a0,
        (vh - vb * k / q + k * k) / a0,
        1.0,
        2 * (k * k - 1) / a0,
        (1 - k / q + k * k) / a0,
    ]

    # Stage 2: the RLB high pass.
    f0 = 38.13547087602444
    q = 0.5003270373238773
    k = tan(pi * f0 / rate)
    a0 = 1 + k / q + k * k
    highpass = [1.0, -2.0, 1.0, 1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]

    return np.array([shelf, highpass])
