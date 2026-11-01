"""What the advisor knows of the people at home: when they sleep (CAHIER-MOTEUR.md § 10.3, § 11).

What touches the people is a setting, never a guess fixed in the code (Frank, 31 October): the sleeping hours are set
for each room, 22:00 to 7:00 when nothing is set, and the alarm armed for the night counts as sleep too.
"""
from dataclasses import dataclass
from datetime import datetime, time, timedelta

NIGHT_ALARM = "armed_night"
# Durations are found five minutes at a time, the twin's own step; later moments a quarter of an hour at a time.
STEP_MINUTES, LATER_STEP = 5, 15


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
    # The longest airing, the furthest « vers 16 h », the longest run of the VMC's fast speed or the purifier (minutes):
    # within them the advisor finds the shortest that is enough, five minutes at a time (Frank, 1 November: « il faut 6
    # min, il dit Aérez 10 min »).
    airing_max: int = 30
    later_max: int = 120
    devices_max: int = 60
    tonight_before: float = 4.0             # hours before bedtime « Cette nuit, pensez à… » is said
    mist_before: float = 5.0                # hours before bedtime misted panes are said
    frost_guard: float = 7.0                # °C the house is kept above while away for days
    tolerance: float = 1.0                  # « tolérance aux gestes »: more than 1, fewer gestures; less, more
    not_now: int = 60                       # minutes a gesture answered « Pas maintenant » is put aside
    # The stove that does not stop by itself (Frank, 1 November): said worth stopping when the room would stay in its
    # range this many hours without it — lighting it again costs pellets and wear —, and « Coupez le poêle » once the
    # room has stayed this much above its set point for this long.
    stove_hold: float = 3.0                 # hours
    overheat: float = 1.0                   # °C
    overheat_minutes: int = 30              # minutes

    KEYS = {"ouvrir_la_nuit": "open_at_night", "aeration_max_min": "airing_max", "plus_tard_max_min": "later_max",
            "appareils_max_min": "devices_max", "cette_nuit_avant_h": "tonight_before", "buee_avant_h": "mist_before",
            "hors_gel": "frost_guard", "tolerance": "tolerance", "pas_maintenant_min": "not_now",
            "poele_tient_h": "stove_hold", "depassement": "overheat", "depassement_min": "overheat_minutes"}

    @property
    def airings(self) -> tuple[int, ...]:
        """The airings compared: 5, 10… up to the longest."""
        return tuple(range(STEP_MINUTES, max(self.airing_max, STEP_MINUTES) + 1, STEP_MINUTES))

    @property
    def later(self) -> tuple[int, ...]:
        """The later moments compared: every quarter of an hour up to the furthest (« vers 16 h 15 »)."""
        return tuple(range(LATER_STEP, max(self.later_max, LATER_STEP) + 1, LATER_STEP))

    @property
    def devices(self) -> tuple[int, ...]:
        """The runs of a device compared: 10, 15… up to the longest."""
        return tuple(range(2 * STEP_MINUTES, max(self.devices_max, 2 * STEP_MINUTES) + 1, STEP_MINUTES))

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
