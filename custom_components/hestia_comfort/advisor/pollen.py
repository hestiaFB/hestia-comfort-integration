"""Days of high pollens, for a household that said someone at home is allergic (« Réglages du foyer »).

Validated by Frank on 6 November 2026, Confort 2.1.0b2's rule brought into the engine 3:
- the humidity, the mould and the CO₂ keep the airing they need, at any hour (FREE) — capped at AIRING, the rejeu of 3 to
  6 November lost Chambre A's airings for its humidity, too short to change anything;
- cooling the room or clearing an odour or particles waits for a good moment — the first MORNING hours after waking up,
  or the hour after the rain (RINSED) — and lasts AIRING minutes at most, never « Ouvrez » without an end;
- a window already open is shut after AIRING minutes, unless it helps the humidity, the mould or the CO₂;
- no window left open for the night (« Cette nuit, pensez à… »).
Hestia Weather says the day's level (api.pollen, 0 none to 4 very high, `high` from 3); nothing is guessed without it.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .household import Sleep

AIRING = 10             # minutes an airing lasts at most
RINSED = 60             # minutes the air stays washed of pollens after the rain
MORNING = 2.0           # hours after waking up: the early morning, when the air holds the fewest pollens
HIGH = 3                # Hestia Weather's level from which the pollens are high
# What an airing may be for at any hour: the dwelling and the air one breathes come first (Confort 2.1: « une aération
# utile pour l'humidité ou le CO₂ reste toujours conseillée, même les jours de pollens »).
FREE = ("humidity", "mould", "co2")


@dataclass(frozen=True)
class Pollen:
    """The day's high pollens, as the advisor uses them."""
    level: int                                      # 3 high, 4 very high
    main: str | None = None                         # the species that weighs most, as Hestia Weather names it
    # The good moments, in minutes from now, (start, end): the early morning, the hour after the rain.
    good: tuple[tuple[float, float], ...] = ()
    after_rain: bool = False                        # the rain washed the air within the last RINSED minutes
    open_for: float | None = None                   # minutes the room's windows have been open; None: shut

    def good_at(self, minutes: float = 0) -> bool:
        """Whether `minutes` from now is a good moment to air for something other than FREE."""
        return any(start <= minutes < end for start, end in self.good)

    def left(self) -> float:
        """Minutes the window open now may stay open."""
        return max(0.0, AIRING - (self.open_for or 0.0))


def today(found: dict | None, local: datetime, sleep: Sleep = Sleep(), rained_at: datetime | None = None,
          raining: bool = False, open_since: datetime | None = None) -> Pollen | None:
    """The day's pollens when they are high, from Hestia Weather's api.pollen (`found`, given only when someone at home is
    allergic); None otherwise. `local`: now, aware; `rained_at`: when the rain was last measured falling; `open_since`:
    when the room's windows were opened, None when shut."""
    if not isinstance(found, dict) or found.get("high") is not True:
        return None
    level = found.get("level")
    good = []
    # This morning's waking and tomorrow's: from each, MORNING hours.
    for days in (0, 1):
        day = local + timedelta(days=days)
        at = sleep.end_on(day.date())
        wake = day.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
        start = (wake - local).total_seconds() / 60
        good.append((start, start + MORNING * 60))
    after_rain = False
    if rained_at is not None and not raining:
        since = (local - rained_at).total_seconds() / 60
        if 0 <= since < RINSED:
            after_rain = True
            good.append((-since, RINSED - since))
    open_for = None if open_since is None else max(0.0, (local - open_since).total_seconds() / 60)
    return Pollen(level=level if isinstance(level, int) else HIGH, main=found.get("main"),
                  good=tuple(sorted(good)), after_rain=after_rain, open_for=open_for)
