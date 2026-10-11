"""One streaming pass over an episode.

Audio is fed in chunks and reduced to 100 ms frames of mean square power,
so an hour of stereo audio costs a few hundred kilobytes of state instead of
a gigabyte of samples. Every measurement is computed from those frames.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import resample_poly, sosfilt

from .kweight import k_weighting_sos

FRAME_SECONDS = 0.1
OVERSAMPLE = 4
TP_OVERLAP = 16  # input samples of context around each chunk for the oversampler
CLIP_LEVEL = 0.999  # |sample| at or above this counts as full scale
CLIP_MIN_RUN = 3  # consecutive full-scale samples before we call it a clip
MAX_EVENTS = 1000


@dataclass
class Frames:
    rate: int
    channels: int
    samples: int  # total samples per channel, including any partial last frame
    frame_len: int
    kpower: np.ndarray  # (frames, channels) K-weighted mean square
    power: np.ndarray  # (frames, channels) plain mean square
    sample_peak: float = 0.0  # linear, all channels
    true_peak: float = 0.0  # linear, 4x oversampled
    clips: list = field(default_factory=list)  # (start sample, channel, run length)
    clip_count: int = 0
    sums: np.ndarray | None = None  # per-channel sample sums, for DC offset

    @property
    def duration(self) -> float:
        return self.samples / self.rate


class Analyzer:
    def __init__(self, rate: int, channels: int):
        self.rate = rate
        self.channels = channels
        self.frame_len = max(1, round(rate * FRAME_SECONDS))
        self._sos = k_weighting_sos(rate)
        self._zi = np.zeros((2, 2, channels))
        self._carry = np.zeros((0, channels))
        self._kcarry = np.zeros((0, channels))
        self._kpower: list[np.ndarray] = []
        self._power: list[np.ndarray] = []
        self.samples = 0
        self.sample_peak = 0.0
        self.true_peak = 0.0
        self._tp_tail = np.zeros((2 * TP_OVERLAP, channels))
        self._run = np.zeros(channels, dtype=np.int64)  # open full-scale run per channel
        self.clips: list[tuple[int, int, int]] = []
        self.clip_count = 0
        self._sums = np.zeros(channels)

    def feed(self, chunk: np.ndarray) -> None:
        chunk = np.asarray(chunk, dtype=np.float64)
        if chunk.ndim == 1:
            chunk = chunk[:, None]
        if chunk.shape[1] != self.channels:
            raise ValueError(f"expected {self.channels} channels, got {chunk.shape[1]}")
        self._find_clips(chunk, self.samples)
        self._sums += chunk.sum(axis=0)
        self.samples += len(chunk)
        weighted, self._zi = sosfilt(self._sos, chunk, axis=0, zi=self._zi)
        self._carry = self._frame(np.concatenate([self._carry, chunk]), self._power)
        self._kcarry = self._frame(np.concatenate([self._kcarry, weighted]), self._kpower)
        if len(chunk):
            self.sample_peak = max(self.sample_peak, float(np.abs(chunk).max()))
        self._true_peak(chunk)

    def _find_clips(self, chunk: np.ndarray, offset: int) -> None:
        full = np.abs(chunk) >= CLIP_LEVEL
        n = len(chunk)
        for ch in range(self.channels):
            col = full[:, ch]
            run = int(self._run[ch])  # open run that ended the previous chunk
            self._run[ch] = 0
            if run and not (n and col[0]):
                self._close_run(offset - run, ch, run)
            if not col.any():
                continue
            edges = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
            for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True):
                start, length = offset + a, b - a
                if a == 0 and run:
                    start, length = offset - run, length + run
                if b == n:
                    self._run[ch] = length  # may continue into the next chunk
                else:
                    self._close_run(start, ch, length)

    def _close_run(self, start: int, ch: int, length: int) -> None:
        if length >= CLIP_MIN_RUN:
            self.clip_count += 1
            if len(self.clips) < MAX_EVENTS:
                self.clips.append((start, ch, length))

    def _true_peak(self, chunk: np.ndarray) -> None:
        # Oversample with context on both sides; the last TP_OVERLAP samples are
        # left for the next call, which sees what follows them.
        buf = np.concatenate([self._tp_tail, chunk])
        self._tp_tail = buf[-2 * TP_OVERLAP :]
        up = resample_poly(buf, OVERSAMPLE, 1, axis=0)
        valid = up[TP_OVERLAP * OVERSAMPLE : (len(buf) - TP_OVERLAP) * OVERSAMPLE]
        if len(valid):
            self.true_peak = max(self.true_peak, float(np.abs(valid).max()))

    def _frame(self, data: np.ndarray, out: list[np.ndarray]) -> np.ndarray:
        n = len(data) // self.frame_len
        if n:
            whole = data[: n * self.frame_len].reshape(n, self.frame_len, self.channels)
            out.append(np.mean(whole**2, axis=1))
        return data[n * self.frame_len :]

    def finish(self) -> Frames:
        self._true_peak(np.zeros((TP_OVERLAP, self.channels)))
        for ch, run in enumerate(self._run):
            if run:
                self._close_run(self.samples - int(run), ch, int(run))
        self.true_peak = max(self.true_peak, self.sample_peak)
        empty = np.zeros((0, self.channels))
        return Frames(
            rate=self.rate,
            channels=self.channels,
            samples=self.samples,
            frame_len=self.frame_len,
            kpower=np.concatenate(self._kpower) if self._kpower else empty,
            power=np.concatenate(self._power) if self._power else empty,
            sample_peak=self.sample_peak,
            true_peak=self.true_peak,
            clips=sorted(self.clips),
            clip_count=self.clip_count,
            sums=self._sums.copy(),
        )


def analyze_array(samples: np.ndarray, rate: int, chunk: int = 65536) -> Frames:
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim == 1:
        samples = samples[:, None]
    an = Analyzer(rate, samples.shape[1])
    for start in range(0, len(samples), chunk):
        an.feed(samples[start : start + chunk])
    return an.finish()
