"""episodeqc command line."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyze import analyze_file
from .checks import FAIL, WARN, run_checks
from .fix import suggest_gain
from .measure import measure
from .normalize import NeedsLimiter, normalize
from .profiles import BUILTIN, Profile, ProfileError, load_profile
from .report import EpisodeReport, as_json, github, markdown, text
from .series import check_series

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


def run_normalize(args, profile: Profile) -> int:
    # Keep each folder's layout under --out, so season1/ep01.wav and
    # season2/ep01.wav do not overwrite each other.
    jobs = [
        (f, args.out / (f.relative_to(p) if p.is_dir() else f.name))
        for p in args.paths
        for f in expand([p])
    ]
    if not jobs:
        print("episodeqc: no audio files found", file=sys.stderr)
        return 2
    status = 0
    for src, dst in jobs:
        if dst.resolve() == src.resolve():
            print(f"episodeqc: {src}: output would overwrite the input", file=sys.stderr)
            return 2
        try:
            fix = normalize(src, dst, profile)
        except NeedsLimiter as e:
            print(f"{src}: skipped, {e}")
            status = 1
            continue
        print(f"{src} -> {dst}: {fix.describe() if fix else 'already on target, copied'}")
    return status


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
    c.add_argument("-f", "--format", choices=["text", "json", "github", "markdown"], default="text")
    c.add_argument(
        "--series-tolerance",
        type=float,
        default=1.5,
        metavar="LU",
        help="warn when an episode is this far from the season median (default 1.5)",
    )
    c.add_argument("--no-series", action="store_true", help="skip the season consistency check")
    c.add_argument("--strict", action="store_true", help="treat warnings as failures")
    c.add_argument("-v", "--verbose", action="store_true", help="show passing checks too")

    n = sub.add_parser("normalize", help="write level-corrected copies of episodes")
    n.add_argument("paths", nargs="+", type=Path, help="audio files or folders")
    n.add_argument("-o", "--out", type=Path, required=True, help="output folder")
    n.add_argument("-p", "--profile", default="podcast")

    args = ap.parse_args(argv)
    try:
        profile = resolve_profile(args.profile)
    except ProfileError as e:
        print(f"episodeqc: {e}", file=sys.stderr)
        return 2
    if args.cmd == "normalize":
        return run_normalize(args, profile)

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

    if not args.no_series:
        check_series(reports, args.series_tolerance)

    if args.format == "json":
        print(as_json(reports, profile.name))
    elif args.format == "github":
        print(github(reports))
    elif args.format == "markdown":
        print(markdown(reports, profile.name))
    else:
        print(text(reports, verbose=args.verbose))
    if errors:
        return 2
    bad = {FAIL, WARN} if args.strict else {FAIL}
    return 1 if any(r.status in bad for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
