"""Turn checked episodes into something a person or a CI system can read."""

from dataclasses import dataclass

from .checks import FAIL, PASS, WARN, Result, worst
from .fix import GainFix
from .measure import Measurements

MARK = {PASS: "ok  ", WARN: "warn", FAIL: "FAIL"}


@dataclass
class EpisodeReport:
    path: str
    measurements: Measurements
    results: list[Result]
    fix: GainFix | None = None

    @property
    def status(self) -> str:
        return worst(self.results)


def text(reports: list[EpisodeReport], verbose: bool = False) -> str:
    lines = []
    for rep in reports:
        m = rep.measurements
        lines.append(f"{rep.path}  [{rep.status.upper()}]")
        lines.append(
            f"  {m.integrated:.1f} LUFS, LRA {m.lra:.1f} LU, true peak "
            f"{m.true_peak:.1f} dBTP, {m.duration:.1f} s"
        )
        for r in rep.results:
            if verbose or r.status != PASS:
                lines.append(f"  {MARK[r.status]}  {r.check}: {r.message}")
        if rep.fix:
            lines.append(f"  fix   {rep.fix.describe()}")
    lines.append(summary_line(reports))
    return "\n".join(lines)


def summary_line(reports: list[EpisodeReport]) -> str:
    counts = {s: sum(r.status == s for r in reports) for s in (PASS, WARN, FAIL)}
    n = len(reports)
    return (
        f"{n} episode{'s' if n != 1 else ''}: {counts[PASS]} passed, "
        f"{counts[WARN]} with warnings, {counts[FAIL]} failed"
    )


def as_json(reports: list[EpisodeReport], profile: str) -> str:
    import json
    from dataclasses import asdict

    return json.dumps(
        {
            "profile": profile,
            "summary": summary_line(reports),
            "episodes": [
                {
                    "path": rep.path,
                    "status": rep.status,
                    "measurements": rep.measurements.to_dict(),
                    "checks": [asdict(r) for r in rep.results],
                    "fix": asdict(rep.fix) if rep.fix else None,
                }
                for rep in reports
            ],
        },
        indent=2,
    )


def _escape(s: str, prop: bool = False) -> str:
    s = s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        s = s.replace(":", "%3A").replace(",", "%2C")
    return s


def github(reports: list[EpisodeReport]) -> str:
    """GitHub Actions workflow commands, so problems show up on the run page."""
    lines = []
    for rep in reports:
        for r in rep.results:
            if r.status == PASS:
                continue
            level = "error" if r.status == FAIL else "warning"
            msg = r.message + (
                f" ({rep.fix.describe()})" if r.check == "loudness" and rep.fix else ""
            )
            lines.append(
                f"::{level} file={_escape(rep.path, True)},"
                f"title={_escape('episodeqc ' + r.check, True)}::{_escape(msg)}"
            )
    lines.append(summary_line(reports))
    return "\n".join(lines)


def markdown(reports: list[EpisodeReport], profile: str) -> str:
    """A table for a PR comment or a job summary."""
    icon = {PASS: "✅", WARN: "⚠️", FAIL: "❌"}
    rows = [
        f"### episodeqc: {profile}",
        "",
        "| Episode | Status | Loudness | True peak | LRA | Length | Problems |",
        "|---|---|---|---|---|---|---|",
    ]
    for rep in reports:
        m = rep.measurements
        problems = "; ".join(f"{r.check}: {r.message}" for r in rep.results if r.status != PASS)
        if rep.fix:
            problems += f" (fix: {rep.fix.describe()})"
        problems = problems.replace("|", "\\|") or "none"
        rows.append(
            f"| {rep.path} | {icon[rep.status]} | {m.integrated:.1f} LUFS | "
            f"{m.true_peak:.1f} dBTP | {m.lra:.1f} LU | {m.duration / 60:.1f} min | "
            f"{problems} |"
        )
    rows += ["", summary_line(reports)]
    return "\n".join(rows)
