"""What the advisor knows of the people at home: when they sleep (CAHIER-MOTEUR.md § 10.3, § 11).

What touches the people is a setting, never a guess fixed in the code (Frank, 31 October): the sleeping hours are set
for each room, 22:00 to 7:00 when nothing is set, and the alarm armed for the night counts as sleep too.
"""
from dataclasses import dataclass
from datetime import datetime, time, timedelta

NIGHT_ALARM = "armed_night"


@dataclass(frozen=True)
class Sleep:
    start: time = time(22, 0)
    end: time = time(7, 0)

    @classmethod
    def of(cls, setting: dict | None) -> "Sleep":
        """From a room's setting, {"debut": "22:30", "fin": "06:45"}; the defaults for what is not set."""
        setting = setting or {}
        start, end = setting.get("debut"), setting.get("fin")
        return cls(time.fromisoformat(start) if start else cls.start, time.fromisoformat(end) if end else cls.end)

    def asleep(self, local: datetime, alarm: str | None = None) -> bool:
        if alarm == NIGHT_ALARM:
            return True
        now = local.time()
        return (self.start <= now or now < self.end) if self.start > self.end else self.start <= now < self.end

    def _next(self, local: datetime, at: time) -> datetime:
        found = local.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
        return found if found > local else found + timedelta(days=1)

    def wake(self, local: datetime) -> datetime:
        """The next waking up."""
        return self._next(local, self.end)

    def bedtime(self, local: datetime) -> datetime:
        """The next going to bed."""
        return self._next(local, self.start)
