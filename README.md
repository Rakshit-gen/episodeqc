# episodeqc

Check audio episodes against loudness and delivery specs before they ship.

Audio-series apps publish thousands of episodes a week, more and more of them
voiced or mixed by AI pipelines. A person can't listen to every one of them,
but a script can measure every one. episodeqc catches the problems listeners
actually notice:

- an episode much quieter or louder than the one before it
- clipping and peaks that distort on phone speakers
- dead air in the middle of a scene
- silence (or none) at the start and end
- hiss under the dialogue
- stereo files whose two channels are identical (twice the size for nothing)

For each problem it says where it is. For level problems it also gives the gain
that fixes it, and it tells you when gain alone would push the peaks too high
and the episode needs a limiter instead.

## Quickstart

```
uv tool install git+https://github.com/Rakshit-gen/episodeqc
episodeqc check season1/            # every audio file in the folder
episodeqc check -p acx chapter*.wav # audiobook spec
episodeqc normalize season1/ -o fixed/
```

On a folder of four short generated test episodes (white-noise "speech" with
pauses; the fourth is quieter and has a long hole in the middle):

```
season1/ep01.wav  [PASS]
  -16.0 LUFS, LRA 5.9 LU, true peak -1.9 dBTP, 113.5 s
season1/ep02.wav  [PASS]
  -16.0 LUFS, LRA 4.8 LU, true peak -2.2 dBTP, 110.9 s
season1/ep03.wav  [PASS]
  -16.4 LUFS, LRA 4.2 LU, true peak -2.0 dBTP, 112.1 s
season1/ep04.wav  [FAIL]
  -19.0 LUFS, LRA 5.5 LU, true peak -5.3 dBTP, 118.9 s
  FAIL  loudness: integrated -19.0 LUFS, target -16.0 ± 1.0
  FAIL  dead-air: 1 silences over 5 s: 7.6 s at 0:45
  warn  series: -2.8 LU from the season median (-16.2 LUFS)
  fix   apply +3.0 dB
4 episodes: 3 passed, 0 with warnings, 1 failed
```

Exit codes: `0` all passed (warnings allowed), `1` something failed (or warned,
with `--strict`), `2` a file could not be read or the settings are wrong.

## What it measures

| Measurement | How |
|---|---|
| Integrated loudness (LUFS) | ITU-R BS.1770-4: K-weighting, 400 ms blocks, -70 LUFS absolute gate and -10 LU relative gate |
| Loudness range (LU) | EBU Tech 3342: 3 s short-term loudness every 100 ms, 10th to 95th percentile |
| Momentary / short-term max | 400 ms and 3 s windows |
| True peak (dBTP) | 4x oversampling |
| Sample peak, RMS, noise floor | Plain dBFS; noise floor is the quietest half second, ignoring digital silence |
| Clipping | Runs of 3 or more samples at full scale |
| Silence | 100 ms frames below the profile's threshold: head, tail and gaps |
| DC offset, dual mono | Per-channel mean; identical channels |
| Season consistency | Each episode against the median loudness of the batch |

The K-weighting filter is computed for the file's own sample rate. At 48 kHz
the coefficients match the BS.1770 tables, and the tests check integrated
loudness against [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) on
mixed-level material at 44.1 and 48 kHz (within 0.05 LU).

Files are read in 10 second chunks and reduced to 100 ms power frames, so
memory does not grow with episode length.

## Profiles

```
episodeqc profiles
```

| Profile | What it checks |
|---|---|
| `podcast` (default) | -16 LUFS ± 1, true peak ≤ -1 dBTP, LRA ≤ 15 LU, ≤ 2 s at the head, ≤ 5 s at the tail, no gap over 5 s |
| `ebu-r128` | -23 LUFS ± 0.5, true peak ≤ -1 dBTP |
| `acx` | RMS -23 to -18 dBFS, peak ≤ -3 dBFS, noise floor ≤ -60 dBFS, 0.5-1 s head, 1-5 s tail, 44.1 kHz, ≤ 120 min |

Your own spec goes in a TOML file. It can extend a built-in profile, and
unknown keys are an error so a typo can't switch a check off unnoticed. See
[examples/audio-app.toml](examples/audio-app.toml):

```toml
extends = "podcast"
max_gap = 4.0
lead_silence = [0.0, 1.0]
sample_rates = [44100, 48000]
```

Checks: `loudness`, `true-peak`, `sample-peak`, `loudness-range`,
`lead-silence`, `tail-silence`, `dead-air`, `rms`, `noise-floor`, `clipping`,
`dc-offset`, `dual-mono`, `format`, `duration`, plus `series` across a batch.

## Options

```
episodeqc check PATHS [-p PROFILE] [-f text|json|github|markdown] [--strict]
                      [--disable CHECK] [--series-tolerance LU] [--no-series]
                      [-j JOBS] [-v]
episodeqc normalize PATHS -o OUT [-p PROFILE]
episodeqc profiles
```

`.episodeqc.toml` in the current folder (or `-c FILE`) sets defaults:

```toml
profile = "examples/audio-app.toml"
disable = ["dual-mono"]
strict = true
series_tolerance = 1.0
```

`normalize` writes a copy with the suggested gain, in the input's own format.
It keeps the folder layout and won't overwrite the input. It only applies
plain gain: if reaching the target would push peaks over the limit, it skips
the file and says it needs a limiter.

## In CI

```yaml
- uses: Rakshit-gen/episodeqc@main
  with:
    paths: episodes/
    profile: examples/audio-app.toml
```

Problems show up as annotations on the run, and a table goes to the job summary.

## Measured vs Claimed

| Claim | Value | How measured | Date |
|---|---|---|---|
| Speed | 10 min episode in 5.44 s (110x real time) | `scripts/bench.py 10`: stereo 48 kHz 16-bit WAV, best of 3, Apple M4, Python 3.13 | 2026-10-12 |
| Memory | 246 MB peak RSS, 102 MB of it before analysis started | same run, `ru_maxrss` | 2026-10-12 |
| Loudness accuracy | within 0.05 LU of pyloudnorm | `tests/test_reference.py`, 6 mixed-level signals | 2026-10-12 |
| BS.1770 filter | matches the 48 kHz coefficient tables to 1e-8 | `tests/test_kweight.py` | 2026-10-12 |

## Status

Works: everything above, with 106 tests. Reads anything libsndfile reads
(WAV, FLAC, OGG, AIFF, and MP3 with libsndfile 1.1+).

Not done: AAC/M4A input (convert first), and a built-in limiter, which
`normalize` deliberately leaves to a real mastering tool. Noise floor and
silence use unweighted levels, so low rumble counts the same as hiss.
