from episodeqc.profiles import BUILTIN, Profile


def test_builtins_exist():
    assert {"ebu-r128", "podcast", "acx"} <= set(BUILTIN)


def test_builtin_names_match_keys():
    for name, p in BUILTIN.items():
        assert p.name == name
        assert p.description


def test_defaults_check_little():
    p = Profile(name="bare")
    assert p.loudness is None and p.max_true_peak is None


def test_load_toml(tmp_path):
    from episodeqc.profiles import load_profile

    p = tmp_path / "studio.toml"
    p.write_text(
        "loudness = -18.0\nmax_true_peak = -1.5\nlead_silence = [0.2, 1.0]\n"
        "sample_rates = [44100, 48000]\n"
    )
    prof = load_profile(p)
    assert prof.name == "studio"
    assert prof.loudness == -18.0
    assert prof.lead_silence == (0.2, 1.0)
    assert prof.sample_rates == (44100, 48000)


def test_extends_a_builtin(tmp_path):
    from episodeqc.profiles import load_profile

    p = tmp_path / "app.toml"
    p.write_text('extends = "podcast"\nloudness = -14.0\n')
    prof = load_profile(p)
    assert prof.loudness == -14.0
    assert prof.max_true_peak == -1.0  # kept from podcast


def test_unknown_key_is_an_error(tmp_path):
    import pytest

    from episodeqc.profiles import ProfileError, load_profile

    p = tmp_path / "typo.toml"
    p.write_text("loudnes = -16\n")
    with pytest.raises(ProfileError, match="loudnes"):
        load_profile(p)


def test_bad_silence_range(tmp_path):
    import pytest

    from episodeqc.profiles import ProfileError, load_profile

    p = tmp_path / "bad.toml"
    p.write_text("lead_silence = [2.0, 1.0]\n")
    with pytest.raises(ProfileError):
        load_profile(p)
