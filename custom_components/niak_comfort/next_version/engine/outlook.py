"""The next hours, from the Hestia Weather forecast: when opening will help, when to close, rain coming."""
from datetime import datetime, timedelta


def _at(item) -> datetime | None:
    try:
        return datetime.fromisoformat(item["time"])
    except (KeyError, TypeError, ValueError):
        return None


def slot(hours: list[dict], now: datetime, indoor: float | None, *, hot: bool, cool_now: bool, margin: float,
         horizon: int = 18) -> dict | None:
    """First hour when the outside becomes fresh enough to open, or warmer than inside again (template « créneau »)."""
    if indoor is None or not hot:
        return None
    future = [(t, h) for h in hours if (t := _at(h)) and now < t <= now + timedelta(hours=horizon)
              and isinstance(h.get("temperature"), (int, float))]
    for t, h in sorted(future, key=lambda x: x[0]):
        fresh = h["temperature"] <= indoor - margin
        if (not cool_now and fresh) or (cool_now and h["temperature"] > indoor):
            return {"kind": "close" if cool_now else "open", "time": t.isoformat(), "temperature": h["temperature"],
                    "wind_bearing": h.get("wind_bearing")}
    return None


# Minutes within which a rain known to the minute (Météo-France's radar) shuts the exposed openings.
IMMINENT = 20
# Beyond this, a coming rain changes nothing to the advice of now.
HORIZON = 120


def rain_timing(ahead, hours_until: float | None = None) -> tuple[int | None, bool]:
    """Minutes before the next rain within the horizon, and whether they are known to the minute.

    `ahead` is Hestia Weather's `rain()` (2.6.1); before it, `hours_until` was the index of the first rainy hour."""
    if isinstance(ahead, dict) and isinstance(ahead.get("minutes"), (int, float)) and not isinstance(ahead["minutes"], bool):
        minutes, precise = ahead["minutes"], ahead.get("precision") == "minute"
    elif isinstance(hours_until, (int, float)) and not isinstance(hours_until, bool):
        minutes, precise = hours_until * 60, False
    else:
        return None, False
    if minutes < 0 or minutes > HORIZON:
        return None, False
    return round(minutes), precise
