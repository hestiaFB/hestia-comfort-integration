"""One place to configure: the Hestia Confort page. The native flow only enables it."""
import uuid
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import DOMAIN
from .domain_migration import async_resume


class ComfortConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input and "panel_config" in user_input:
            from .configuration import get_configuration
            service = await get_configuration(self.hass)
            values, warnings = service.validate(user_input["panel_config"])
            values["acknowledged"] = service.ensure_acknowledged(warnings, user_input.get("acknowledged", []))
            # A free room has no Home Assistant area: it gets its own stable identity.
            await self.async_set_unique_id(values["area_id"] or "room_" + uuid.uuid4().hex)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=values["name"], data=values)
        if await async_resume(self.hass):
            # A home installed under the former name is resumed, never set up a second time.
            return self.async_abort(reason="migrated")
        if self.hass.config_entries.async_entries(DOMAIN):
            # Rooms are added from the sidebar page, with explained proposals.
            return self.async_abort(reason="use_panel")
        if user_input is not None:
            await self.async_set_unique_id("hestia_home")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Mon logement", data={"home": True})
        return self.async_show_form(step_id="home", data_schema=vol.Schema({}), last_step=True)

    async def async_step_home(self, user_input=None):
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ComfortOptionsFlow()


class ComfortOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}),
            description_placeholders={"link": "/hestia/confort"})
