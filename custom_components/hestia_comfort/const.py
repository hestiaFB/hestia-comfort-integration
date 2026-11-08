"""Stable keys for the first observation-only alpha."""
DOMAIN = "hestia_comfort"
# The released number, written here and not read from manifest.json: no file is opened when Home Assistant imports the
# module. The panel and the card are cached by their version, so tests/test_version.py checks it follows the manifest
# (stuck at 1.1.4 from 1.2.0-beta.1 to 1.2.5-beta.7).
VERSION = "3.1.0b4"
VIEW_VERSION = 1
# A contact open for less than this is a bounce: shown at once, but advice waits for a real opening.
OPEN_DEBOUNCE_SECONDS = 30
# Seven-day outdoor mean (hourly statistics), refreshed at most this often.
SEASON_REFRESH_SECONDS = 3600
# Right after Home Assistant starts, sensors arrive one by one: silent ones are « loading », not broken.
STARTUP_GRACE_SECONDS = 300
# Past openings are read again from the recorder this often (and soon after each closing).
LEARNING_REFRESH_SECONDS = 6 * 3600
SOURCES = {
    "indoor_temperature": "temperature", "outdoor_temperature": "temperature",
    "indoor_humidity": "humidity", "outdoor_humidity": "humidity", "co2": "co2",
    "illuminance": "illuminance", "pm25": "pm25", "voc": "voc", "purifier": "purifier", "ventilation": "ventilation", "ventilation_boost": "ventilation",
    "rain": "rain", "pollution": "pollution", "heating": "heating", "heating_indicator": "heating_indicator",
    "wind_gust": "wind", "wind_bearing": "bearing", "solar": "irradiance",
}
# Home Assistant areas that describe the outside: offered for exterior sources, never as rooms.
OUTDOOR_AREAS = ("exterieur", "extérieur", "dehors", "jardin", "terrasse", "balcon", "cour", "patio",
                 "outdoor", "outside", "garden", "yard", "terrace", "balcony")
