"""Who the room is for, and whether they are at home: the people chosen for it, and the home's alarm.

A bedroom is for one person, a living room for everyone. Each room may name its people (Home Assistant's `person`
entities): it is then « occupied » when one of them is at home and « empty » when all are away, whatever the rest of
the household does. Without people chosen, the whole home counts, as before.

The alarm (Alarmo, recognised by itself, or any panel the person chooses) says more than presence:
- armed « away » or « vacation »: nobody is at home;
- armed « night »: people are at home, asleep;
- armed at all with a window open: worth saying before leaving or going to bed.
"""

AWAY = ("armed_away", "armed_vacation")
NIGHT = ("armed_night",)
ARMED = ("armed_away", "armed_vacation", "armed_night", "armed_home", "armed_custom_bypass", "arming", "pending", "triggered")
PLATFORM = "alarmo"
NAME = "Alarmo"


def people(states):
    """{"home": [names], "away": [names], "unknown": [names]} from [(name, state)] of `person` entities."""
    out = {"home": [], "away": [], "unknown": []}
    for name, state in states:
        out["home" if state == "home" else "unknown" if state in (None, "unknown", "unavailable") else "away"].append(name)
    return out


def alarm(state):
    """What the alarm says: {"state", "armed", "away", "night"}; None without an alarm."""
    if state in (None, "unknown", "unavailable"):
        return None
    return {"state": state, "armed": state in ARMED, "away": state in AWAY, "night": state in NIGHT}


def occupied(found, panel, zone_count=None):
    """True when the room's people (or, without any, the household) are at home, False when not, None when unknown."""
    if panel and panel["away"]:
        return False
    if found and (found["home"] or found["away"]):
        return bool(found["home"]) if not found["unknown"] or found["home"] else None
    if zone_count is not None:
        return zone_count > 0
    if panel:
        return True
    return None
