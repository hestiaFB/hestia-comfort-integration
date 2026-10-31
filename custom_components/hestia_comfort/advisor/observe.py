"""Layer 1: what the sensors say, read once, for the engine and the card alike.

An observation keeps its origin and its reliability; nothing is ever replaced by a default value. The bounce delay of
a window contact is applied here and only here: the card shows the windows this layer gives, never the raw contact.
"""
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

ORIGINS = ("measured", "weather", "declared", "computed", "learned", "estimated")
# An opening shorter than this is someone going through a French window: it does not count as open yet.
BOUNCE = timedelta(seconds=30)


@dataclass(frozen=True)
class Observation:
    value: float | bool | None
    at: datetime | None
    origin: str = "measured"
    # 0 to 1, set by the reliability layer: under 0.5 the twin's estimate stands in for the measure.
    reliability: float = 1.0
    unit: str | None = None
    source: str | None = None

    @property
    def known(self) -> bool:
        return self.value is not None


class Series:
    """A sample-and-hold series: the value at a time is the last one reported before it.

    A contact that stops answering stays in its series as None: what the window did then is unknown."""

    def __init__(self, points, keep_none=False):
        points = sorted(((t, v) for t, v in points
                         if (v is not None or keep_none) and not (isinstance(v, float) and not math.isfinite(v))),
                        key=lambda p: p[0])
        self.times = [t for t, _ in points]
        self.values = [v for _, v in points]

    def at(self, when):
        i = bisect_right(self.times, when)
        return self.values[i - 1] if i else None

    def since(self, when):
        """When the value held at `when` was reported."""
        i = bisect_right(self.times, when)
        return self.times[i - 1] if i else None


def window_open(series: Series, now: datetime, bounce: timedelta = BOUNCE) -> bool | None:
    """Whether a window counts as open at `now`: an opening younger than the bounce delay does not count yet, a
    closing counts at once. None while the contact does not answer."""
    state = series.at(now)
    if state is not True:
        return state
    since = series.since(now)
    if since is not None and now - since < bounce:
        # Still bouncing: the window counts as it was before this opening.
        before = series.at(since - timedelta(microseconds=1))
        return before if before is not True else True
    return True
