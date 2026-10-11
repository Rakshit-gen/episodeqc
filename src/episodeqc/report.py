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
