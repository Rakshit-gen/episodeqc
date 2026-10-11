"""episodeqc command line."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from .analyze import analyze_file
from .checks import CHECKS, FAIL, WARN, run_checks
from .config import DEFAULT_NAME, ConfigError, load_config
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


def list_profiles() -> str:
    from dataclasses import fields

    lines = []
    for p in BUILTIN.values():
        lines.append(f"{p.name}: {p.description}")
        for f in fields(p):
            v = getattr(p, f.name)
            if f.name in ("name", "description") or v in (None, (), frozenset()):
                continue
            lines.append(f"    {f.name} = {v}")
    lines.append(f"checks: {', '.join(CHECKS)}")
    return "\n".join(lines)


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


def _safe_check(path: Path, profile: Profile):
    try:
        return check_file(path, profile)
    except Exception as e:
        return e


def check_all(files: list[Path], profile: Profile, jobs: int):
    """(path, report or exception) for each file, in the order given."""
    if jobs <= 1 or len(files) < 2:
        return [(f, _safe_check(f, profile)) for f in files]
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(zip(files, pool.map(_safe_check, files, [profile] * len(files)), strict=True))


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
    ap.add_argument(
        "-c", "--config", type=Path, help=f"settings file (default: {DEFAULT_NAME} if present)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check episodes against a delivery profile")
    c.add_argument("paths", nargs="+", type=Path, help="audio files or folders")
    c.add_argument(
        "-p",
        "--profile",
        default=None,
        help="built-in profile name or a TOML file (default: podcast)",
    )
    c.add_argument("-f", "--format", choices=["text", "json", "github", "markdown"], default="text")
    c.add_argument(
        "--series-tolerance",
        type=float,
        default=None,
        metavar="LU",
        help="warn when an episode is this far from the season median (default 1.5)",
    )
    c.add_argument("--no-series", action="store_true", help="skip the season consistency check")
    c.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help="check this many files at once (default 1: easy on a laptop)",
    )
    c.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="CHECK",
        help="skip a check (repeatable), e.g. --disable dual-mono",
    )
    c.add_argument("--strict", action="store_true", help="treat warnings as failures")
    c.add_argument("-v", "--verbose", action="store_true", help="show passing checks too")

    n = sub.add_parser("normalize", help="write level-corrected copies of episodes")
    n.add_argument("paths", nargs="+", type=Path, help="audio files or folders")
    n.add_argument("-o", "--out", type=Path, required=True, help="output folder")
    n.add_argument("-p", "--profile", default=None)

    sub.add_parser("profiles", help="list built-in profiles and checks")

    args = ap.parse_args(argv)
    if args.cmd == "profiles":
        print(list_profiles())
        return 0
    try:
        cfg = load_config(args.config)
        profile = resolve_profile(args.profile or cfg.get("profile", "podcast"))
    except (ProfileError, ConfigError) as e:
        print(f"episodeqc: {e}", file=sys.stderr)
        return 2
    if args.cmd == "normalize":
        return run_normalize(args, profile)
    args.disable = cfg.get("disable", []) + args.disable
    args.strict = args.strict or cfg.get("strict", False)
    if args.series_tolerance is None:
        args.series_tolerance = cfg.get("series_tolerance", 1.5)
    unknown = set(args.disable) - set(CHECKS)
    if unknown:
        print(
            f"episodeqc: unknown check {', '.join(sorted(unknown))} (checks: {', '.join(CHECKS)})",
            file=sys.stderr,
        )
        return 2
    if args.disable:
        profile = replace(profile, disabled=profile.disabled | set(args.disable))

    files = expand(args.paths)
    if not files:
        print("episodeqc: no audio files found", file=sys.stderr)
        return 2
    reports, errors = [], 0
    for path, result in check_all(files, profile, args.jobs):
        if isinstance(result, Exception):  # unreadable or not audio: report it and keep going
            print(f"episodeqc: {path}: {result}", file=sys.stderr)
            errors += 1
        else:
            reports.append(result)

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
