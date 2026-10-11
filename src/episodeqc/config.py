"""Project settings from .episodeqc.toml, so CI and laptops run the same checks."""

import tomllib
from pathlib import Path

DEFAULT_NAME = ".episodeqc.toml"
KEYS = {"profile", "disable", "strict", "series_tolerance"}


class ConfigError(ValueError):
    pass


def load_config(path: Path | None) -> dict:
    """Read the given config, or .episodeqc.toml in the current folder if present."""
    if path is None:
        path = Path(DEFAULT_NAME)
        if not path.is_file():
            return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ConfigError(f"{path}: {e}") from e
    unknown = set(data) - KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown keys {', '.join(sorted(unknown))}")
    if not isinstance(data.get("disable", []), list):
        raise ConfigError(f"{path}: disable must be a list of check names")
    return data
