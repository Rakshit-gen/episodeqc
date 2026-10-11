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
