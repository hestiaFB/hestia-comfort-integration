"""What the room's coordinator and its parts share."""
from datetime import timedelta
from typing import Final

STATE_KINDS: Final = ("window", "heating", "rain", "pollution", "presence", "purifier", "ventilation", "cover", "cover_state", "shutter_auto", "shutter_override", "shutter_sun", "shutter_target", "purifier_speed")
# The sunshine is read as its mean over this long: clouds come and go faster than a shutter is moved.
SUN_SMOOTHING: Final = timedelta(minutes=15)
# Twin samples stored before 1.2.9 counted the other room's windows as this room's own: rebuilt from the history.
TWIN_FORMAT: Final = 3
# What a learning pass reads: ten days every six hours, the last day after a window is shut (the merges keep the rest).
FULL_SPAN: Final = timedelta(days=10)
SHORT_SPAN: Final = timedelta(hours=24)
# Measures that move all the time (a CO₂ every few seconds): their changes are grouped, one refresh at most per
# MEASURE_COOLDOWN (30 s since PLAN-OPTIMISATION.md point 7, agreed by Frank on 6 November: 10 s before); a window, the
# heating, a presence or a cover is shown within a second.
MEASURES: Final = frozenset({"indoor_temperature", "outdoor_temperature", "indoor_humidity", "outdoor_humidity", "co2", "illuminance",
                      "pm25", "voc", "wind_gust", "wind_bearing", "solar"})
MEASURE_COOLDOWN: Final = 30.0
# What belongs to an air shared by rooms open onto each other: a room without its own reads its partner's.
SHARED_SOURCES: Final = ("heating", "heating_indicator", "co2", "voc", "pm25", "purifier", "ventilation", "ventilation_boost")
