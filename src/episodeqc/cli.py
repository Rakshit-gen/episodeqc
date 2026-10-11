"""episodeqc command line."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyze import analyze_file
from .checks import FAIL, run_checks
from .fix import suggest_gain
from .measure import measure
from .profiles import BUILTIN, Profile, ProfileError, load_profile
from .report import EpisodeReport, as_json, text

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".aiff", ".aif"}


def expand(paths: list[Path]) -> list[Path]:
    """Files as given; directories searched recursively for audio, in name order."""
    out = []
    for p in paths:
        if p.is_dir():
            out += sorted(
                f
                for f in p.rglob("*")
                if f.suffix.lower() in AUDIO_EXTS
                and not any(part.startswith(".") for part in f.relative_to(p).parts)
            )
        else:
            out.append(p)
    return out


def resolve_profile(name: str) -> Profile:
    if name in BUILTIN:
        return BUILTIN[name]
    if Path(name).is_file():
        return load_profile(name)
    raise ProfileError(
        f"no built-in profile or file named {name!r} (built-in: {', '.join(BUILTIN)})"
    )


def check_file(path: Path, profile: Profile) -> EpisodeReport:
    m = measure(analyze_file(path), silence_db=profile.silence_db)
    return EpisodeReport(str(path), m, run_checks(m, profile), suggest_gain(m, profile))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="episodeqc", description=__doc__)
    ap.add_argument("--version", action="version", version=f"episodeqc {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check episodes against a delivery profile")
    c.add_argument("paths", nargs="+", type=Path, help="audio files or folders")
    c.add_argument(
        "-p",
        "--profile",
        default="podcast",
        help="built-in profile name or a TOML file (default: podcast)",
    )
    c.add_argument("-f", "--format", choices=["text", "json"], default="text")
    c.add_argument("-v", "--verbose", action="store_true", help="show passing checks too")

    args = ap.parse_args(argv)
    try:
        profile = resolve_profile(args.profile)
    except ProfileError as e:
        print(f"episodeqc: {e}", file=sys.stderr)
        return 2

    files = expand(args.paths)
    if not files:
        print("episodeqc: no audio files found", file=sys.stderr)
        return 2
    reports, errors = [], 0
    for path in files:
        try:
            reports.append(check_file(path, profile))
        except Exception as e:  # unreadable or not audio: report it and keep going
            print(f"episodeqc: {path}: {e}", file=sys.stderr)
            errors += 1

    if args.format == "json":
        print(as_json(reports, profile.name))
    else:
        print(text(reports, verbose=args.verbose))
    if errors:
        return 2
    return 1 if any(r.status == FAIL for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
