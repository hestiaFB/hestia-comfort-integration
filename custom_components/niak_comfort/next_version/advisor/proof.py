"""How sure the advisor is of an effect: supposed, reinforced, proven (CAHIER-MOTEUR.md § 4.1).

An effect is what a gesture does to one subject in one room: airing on the heat, on the humidity, on the CO₂… It is
supposed from geometry and ordinary values alone, reinforced when the measures of the moment back it, and proven when the
room showed it: learned over past gestures, or seen now while the gesture lasts. Only a proven effect sends a gesture to
the banner as soon as it is significant; a reinforced one must be clear-cut, and is said in the conditional; a supposed
one only speaks in « Bon à savoir ».
"""
SUPPOSED, REINFORCED, PROVEN = "supposed", "reinforced", "proven"
ORDER = (SUPPOSED, REINFORCED, PROVEN)

# Learned: at least this many gestures, the twin right on the direction and on the order of magnitude — the middle of
# the last RECENT notes (advisor/notes.py) between half and twice the effect announced. A gesture's case: its effect
# announced and its effect measured, both against the twin without it, an hour after it ended.
CASES, RECENT = 3, 10
LOW, HIGH = 0.5, 2.0
# Seen now: the gesture lasts since this long at least, and the measure moved the forecast way by this share of the
# significant gap (decide.SIGNIFICANT) at least.
LIVE_MINUTES, LIVE_SHARE = 15, 0.5
# Reinforced for an open window: a gap between the room and the outside air this large at least (°C; g/m³ of water).
HEAT_GAP, WATER_GAP = 3.0, 1.0


def _ratios(cases) -> list[float]:
    return [m / f for f, m in cases if f and m is not None]


def learned(cases) -> bool:
    """Whether past gestures prove an effect: `cases`, (announced, measured) effects of each gesture, oldest first."""
    ratios = sorted(_ratios(cases)[-RECENT:])
    if len(ratios) < CASES:
        return False
    half = len(ratios) // 2
    middle = ratios[half] if len(ratios) % 2 else (ratios[half - 1] + ratios[half]) / 2
    return LOW <= middle <= HIGH


# Belied: the last this many gestures in a row each did under LOW of the effect announced — or the other way (notes « 0 »
# or « − », Frank, 3 November). The window then promises less than the moment says (Chambre P, 3 November: two airings, the humidity back
# where it was ten minutes after shutting): the effect goes back to supposed, a passive « À essayer », whatever the
# moment backs, until the gestures say otherwise.
BELIED = 2


def belied(cases) -> bool:
    """Whether the last gestures belie the effect the twin gives: each did far under it, or the other way."""
    ratios = _ratios(cases)
    return len(ratios) >= BELIED and all(r < LOW for r in ratios[-BELIED:])


def live(change: float | None, direction: float, significant: float, minutes: float | None) -> bool:
    """Whether the gesture under way shows its effect now: `change`, the measure since it began; `direction`, the sign
    the twin forecasts for it; `significant`, the subject's significant gap."""
    if change is None or minutes is None or minutes < LIVE_MINUTES or direction == 0:
        return False
    return change * (1 if direction > 0 else -1) >= LIVE_SHARE * significant


def window_reinforced(subject: str, air: float, outdoor: float, water: float | None = None,
                      outdoor_water: float | None = None, measured: bool = True) -> bool:
    """Whether the measures of the moment back what an open window does to `subject`: a clear gap between the room and the
    outside air for the heat and the humidity; for the CO₂ and the particles, a sensor in the room is enough — the outside
    air always holds less of them."""
    if subject == "heat":
        return abs(air - outdoor) >= HEAT_GAP
    if subject == "humidity":
        return water is not None and outdoor_water is not None and water - outdoor_water >= WATER_GAP
    if subject in ("co2", "particles", "voc"):
        return measured
    return False


def level(cases=(), reinforced: bool = False, seen: bool = False) -> str:
    """The effect's level: proven when seen now; supposed when the last gestures belie it, whatever came before; proven
    when learned; reinforced when the moment backs it, supposed otherwise."""
    if seen:
        return PROVEN
    if belied(cases):
        return SUPPOSED
    if learned(cases):
        return PROVEN
    return REINFORCED if reinforced else SUPPOSED
