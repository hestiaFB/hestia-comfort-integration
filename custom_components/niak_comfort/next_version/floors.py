"""Read Home Assistant's floor registry without copying its configuration."""
from homeassistant.helpers import area_registry as ar, floor_registry as fr


def floor_catalog(hass):
    return sorted(({"floor_id": f.floor_id, "name": f.name, "level": f.level}
                   for f in fr.async_get(hass).async_list_floors()),
                  key=lambda f: (f["level"] is None, f["level"] or 0, f["name"].casefold(), f["floor_id"]))


def room_floor(hass, config):
    area_id = config.get("area_id")
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    # A linked area is authoritative, including when removed or not assigned.
    if area_id:
        floor_id = area.floor_id if area else None
    else:
        floor_id = config.get("floor_id")
    floor = fr.async_get(hass).async_get_floor(floor_id) if floor_id else None
    return {"floor_id": floor.floor_id, "name": floor.name, "level": floor.level} if floor else None
