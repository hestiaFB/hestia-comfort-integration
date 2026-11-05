"""The heating's schedule, read from the integration that plans it: when the room's heating changes next.

Two are recognised by themselves, ha-chauffage first, then Scheduler; each gives the same change, {"at", "preset",
"name", "temperature", "override"}.

ha-chauffage (armellarcier/ha-chauffage):

ha-chauffage plans the presets of each thermostat over the week and sends them at each slot. For each scheduled
thermostat it gives, on a device of its own linked to the thermostat's:

- « Préréglage prévu » (`…_schedule`): the preset planned now; its attributes the next different one
  (`next_preset`, `next_preset_name`), its start (`next_start`) and the temperature of each preset on this thermostat
  (`temperatures`). It reads the active schedule only;
- « Dérogation » (`…_override`): on while the person changed the thermostat by hand, until `end`. ha-chauffage then
  sends nothing before `end`, and the slot running at that time is applied: the announced `next_start` may never come;
- « Prochain changement » (`…_next_change`, proposed in armellarcier/ha-chauffage#82): a timestamp, the next real
  change, end of an override included, with `preset`, `preset_name` and `temperature`. Read first when it is there.

Scheduler (nielsfaber/scheduler-component): one switch per schedule (`switch.schedule_…`), on while it runs, with
the `entities` it drives, one action per time slot (`actions`, `timeslots`), the slot running (`current_slot`) and the
next one with its start (`next_slot`, `next_trigger`). A Versatile Thermostat driven by presets gives the temperature of
each (`preset_temperatures`). Its conditions (a workday, someone home) may skip a slot: Hestia-FB does not foresee them.

Hestia-FB reads them and commands nothing. Nothing here is guessed: a change whose time is unknown or past is none.
"""
from collections.abc import Mapping
from datetime import datetime

PLATFORM = "chauffage"
NAME = "ha-chauffage"
SCHEDULER = "scheduler"
SCHEDULER_NAME = "Scheduler"
# A schedule that runs: « triggered » for a moment as one of its slots starts.
RUNNING = ("on", "triggered")
# The integrations read, in their order: their keys are also their switches in the general settings.
PLANNERS = (PLATFORM, SCHEDULER)
# The end of each entity's unique id (`{entry_id}_{climate}_{key}`), by role.
KEYS = {"planned": "schedule", "override": "override", "next_change": "next_change"}
GONE = ("unknown", "unavailable", "", None)
# The modes a change may switch the heating back on with (Scheduler's climate.set_hvac_mode).
TURNS_ON = ("heat", "auto", "heat_cool")
# The stops a Versatile Thermostat lifts by itself (engine/thermostat.py): the schedule still holds behind them.
PAUSES = ("window", "auto_start_stop", "sleep", "safety", "inhibition")


def _moment(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _change(at, preset, name, temperature, now, override=False):
    at = _moment(at)
    if at is None or at.tzinfo is None or (now is not None and at <= now):
        return None
    return {"at": at.isoformat(), "preset": preset or None, "name": name or preset or None,
            "temperature": _number(temperature), "override": override}


def next_change(planned=None, override=None, change=None, now=None):
    """The thermostat's next change, from ha-chauffage's entities as (state, attributes): {"at" (ISO), "preset",
    "name", "temperature", "override"} — the preset is None when it is not known —, or None."""
    if change and change[0] not in GONE:
        attrs = change[1] or {}
        return _change(change[0], attrs.get("preset"), attrs.get("preset_name"), attrs.get("temperature"), now)
    if not planned or planned[0] in GONE:
        return None
    attrs = planned[1] or {}
    temperatures = attrs.get("temperatures") if isinstance(attrs.get("temperatures"), dict) else {}
    start = _moment(attrs.get("next_start"))
    if override and override[0] == "on":
        # Until its end ha-chauffage sends nothing; then the slot of that moment: the one planned now if it still runs.
        end = _moment((override[1] or {}).get("end"))
        if end is None:
            return None
        if start is None or end < start:
            return _change(end, planned[0], attrs.get("preset_name"), temperatures.get(planned[0]), now, override=True)
        return _change(end, None, None, None, now, override=True)
    next_preset = attrs.get("next_preset")
    return _change(start, next_preset, attrs.get("next_preset_name"), temperatures.get(next_preset), now)


def _target(action, temperatures):
    """What one Scheduler action sends a thermostat: (preset or mode, temperature); (None, None) for anything else."""
    service, data = action.get("service"), action.get("data") or action.get("service_data") or {}
    if service == "climate.set_temperature":
        return None, _number(data.get("temperature"))
    if service == "climate.set_preset_mode" and data.get("preset_mode"):
        preset = str(data["preset_mode"])
        # A preset temperature of 0 is a preset the thermostat does not use (engine/thermostat.py).
        return preset, _number(temperatures.get(f"{preset}_temp")) or None
    if service == "climate.set_hvac_mode" and data.get("hvac_mode"):
        return str(data["hvac_mode"]), None
    return None, None


def _clock(slot):
    """« 20:30:00 - 00:00:00 » → (20, 30); None for a slot set by the sun (« sunrise+00:30 »)."""
    try:
        hours, minutes = (int(x) for x in str(slot).split(" - ")[0].split(":")[:2])
    except ValueError:
        return None
    return hours, minutes


def is_schedule(attrs):
    """A switch shaped like one of Scheduler's schedules, wherever it comes from: what it drives, its actions, its slots."""
    return (isinstance(attrs, Mapping) and isinstance(attrs.get("entities"), (list, tuple))
            and isinstance(attrs.get("actions"), list) and isinstance(attrs.get("timeslots"), list)
            and "next_trigger" in attrs)


def scheduler_change(state, attrs, temperatures=None, now=None):
    """The next change one Scheduler schedule brings its thermostats, or None. A slot sending what the running one sends
    changes nothing: the first slot that differs is said, later the same day; beyond, nothing is known."""
    attrs = attrs if isinstance(attrs, dict) else {}
    actions, slots, current, k = attrs.get("actions"), attrs.get("timeslots"), attrs.get("current_slot"), attrs.get("next_slot")
    at = _moment(attrs.get("next_trigger"))
    if (state not in RUNNING or at is None or not isinstance(actions, list) or not isinstance(slots, list)
            or len(actions) != len(slots) or not isinstance(k, int) or not 0 <= k < len(actions)):
        return None
    first = k
    if isinstance(current, int) and 0 <= current < len(actions):
        while k < len(actions) and actions[k] == actions[current]:
            k += 1
        if k == len(actions):
            return None
    if k != first:
        start, clock = _clock(slots[first]), _clock(slots[k])
        if start is None or clock is None or clock <= start:
            return None
        at = at.replace(hour=clock[0], minute=clock[1], second=0, microsecond=0)
    action = actions[k] if isinstance(actions[k], dict) else {}
    preset, temperature = _target(action, temperatures if isinstance(temperatures, dict) else {})
    if preset is None and temperature is None:
        return None
    return _change(at, preset, None, temperature, now)


def heard(change, heated=True, off=False, reason=None):
    """The change, when it does something: none in a room declared unheated, none while the heating is switched off
    (the summer) unless it switches it back on; a pause the thermostat lifts by itself (an open window) keeps it."""
    if not change or not heated:
        return None
    if off and reason not in PAUSES and change.get("preset") not in TURNS_ON:
        return None
    return change


def earliest(changes):
    """The soonest of several schedules' changes for one thermostat."""
    found = [c for c in changes if c]
    return min(found, key=lambda c: _moment(c["at"])) if found else None

