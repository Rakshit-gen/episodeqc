import numpy as np


def sine(freq=1000.0, seconds=5.0, rate=48000, amp=1.0, channels=1, phase=0.0):
    t = np.arange(round(seconds * rate)) / rate
    x = amp * np.sin(2 * np.pi * freq * t + phase)
    return np.repeat(x[:, None], channels, axis=1)


def noise(seconds=5.0, rate=48000, amp=0.1, channels=2, seed=0):
    rng = np.random.default_rng(seed)
    return amp * rng.standard_normal((round(seconds * rate), channels))
