import numpy as np

from episodeqc.kweight import k_weighting_sos


def test_matches_bs1770_table_at_48k():
    sos = k_weighting_sos(48000)
    # Coefficients printed in ITU-R BS.1770-4, tables 1 and 2.
    np.testing.assert_allclose(
        sos[0],
        [
            1.53512485958697,
            -2.69169618940638,
            1.19839281085285,
            1,
            -1.69065929318241,
            0.73248077421585,
        ],
        atol=1e-8,
    )
    np.testing.assert_allclose(
        sos[1], [1, -2, 1, 1, -1.99004745483398, 0.99007225036621], atol=1e-8
    )


def test_other_rates_are_stable():
    for rate in (8000, 16000, 22050, 44100, 96000):
        sos = k_weighting_sos(rate)
        for section in sos:
            poles = np.roots(section[3:])
            assert np.all(np.abs(poles) < 1)
