"""Season-level check: episodes of one series should sound equally loud.

Listeners binge. If episode 7 is 3 LU quieter than episodes 6 and 8, they
notice, even when every episode is inside the profile's tolerance on its own.
"""

import math
import statistics

from .checks import PASS, WARN, Result
from .report import EpisodeReport

MIN_EPISODES = 3


def check_series(reports: list[EpisodeReport], tolerance: float = 1.5) -> float | None:
    """Add a 'series' result to each report. Returns the season median, if there is one."""
    levels = [
        r.measurements.integrated for r in reports if not math.isinf(r.measurements.integrated)
    ]
    if len(levels) < MIN_EPISODES:
        return None
    median = statistics.median(levels)
    for rep in reports:
        lufs = rep.measurements.integrated
        if math.isinf(lufs):
            continue
        off = lufs - median
        msg = f"{off:+.1f} LU from the season median ({median:.1f} LUFS)"
        rep.results.append(Result("series", WARN if abs(off) > tolerance else PASS, msg))
    return median
