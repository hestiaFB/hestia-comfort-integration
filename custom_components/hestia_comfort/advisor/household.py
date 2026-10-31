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


@dataclass(frozen=True)
class Habits:
    """The household's way of life, as set (CAHIER-MOTEUR.md § 10.3, « Réglages du foyer »): for the house, and for a
    room where it differs. Each has a default; the physics and the rules of proof are not settings."""
    sleep: Sleep = Sleep()
    open_at_night: bool = False             # whether anyone would get up to open a window at night
    airings: tuple[int, ...] = (10, 20)     # minutes of the airings proposed
    later: tuple[int, ...] = (60, 120)      # minutes ahead of a gesture said « vers 16 h »
    devices: tuple[int, ...] = (30, 60)     # minutes a VMC's fast speed or a purifier is proposed for
    tonight_before: float = 4.0             # hours before bedtime « Cette nuit, pensez à… » is said
    mist_before: float = 5.0                # hours before bedtime misted panes are said
    frost_guard: float = 7.0                # °C the house is kept above while away for days
    tolerance: float = 1.0                  # « tolérance aux gestes »: more than 1, fewer gestures; less, more

    KEYS = {"ouvrir_la_nuit": "open_at_night", "aerations_min": "airings", "plus_tard_min": "later",
            "appareils_min": "devices", "cette_nuit_avant_h": "tonight_before", "buee_avant_h": "mist_before",
            "hors_gel": "frost_guard", "tolerance": "tolerance"}

    @classmethod
    def of(cls, *settings: dict | None) -> "Habits":
        """From the house's setting then the room's (the room's wins), with the French keys of rooms.json « foyer »."""
        merged = {}
        for setting in settings:
            merged.update(setting or {})
        values = {name: (tuple(merged[key]) if isinstance(merged[key], list) else merged[key])
                  for key, name in cls.KEYS.items() if key in merged}
        return cls(sleep=Sleep.of(merged.get("sommeil")), **values)

    def setting(self) -> dict:
        """Back as a setting: what a snapshot keeps."""
        out = {key: (list(v) if isinstance(v := getattr(self, name), tuple) else v) for key, name in self.KEYS.items()}
        out["sommeil"] = {"debut": self.sleep.start.strftime("%H:%M"), "fin": self.sleep.end.strftime("%H:%M")}
        return out
