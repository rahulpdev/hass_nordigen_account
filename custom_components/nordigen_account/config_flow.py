import logging
import voluptuous as vol
from datetime import datetime

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_SECRET_ID,
    CONF_SECRET_KEY,
    CONF_REQUISITION_ID,
    CONF_REFRESH_TOKEN
)
import nordigen_account

_LOGGER = logging.getLogger(__name__)


class NordigenAccountConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nordigen Account."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of user input."""
        errors = {}

        if user_input is not None:
            secret_id = user_input[CONF_SECRET_ID].strip()
            secret_key = user_input[CONF_SECRET_KEY].strip()
            requisition_id = user_input[CONF_REQUISITION_ID].strip()
            if user_input.get(CONF_REFRESH_TOKEN):
                refresh_token = user_input.get(CONF_REFRESH_TOKEN, "").strip()
            else:
                refresh_token = None

            try:
                # Call Nordigen client to create or refresh token
                client, new_refresh_token = await self.hass.async_add_executor_job(
                    nordigen_account.create_nordigen_client,
                    secret_id,
                    secret_key,
                    refresh_token
                )

                # Store user input and new refresh token in the config entry
                data = {
                    CONF_SECRET_ID: secret_id,
                    CONF_SECRET_KEY: secret_key,
                    CONF_REQUISITION_ID: requisition_id,
                    CONF_REFRESH_TOKEN: new_refresh_token
                }

                # Set the secret_id as the unique ID to prevent duplicate integrations
                await self.async_set_unique_id(secret_id)
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(title="Nordigen Account {requisition_id}", data=data)

            except KeyError as e:
                _LOGGER.error("Missing key in token response: %s", str(e))
                errors["base"] = "invalid_token"
            except RuntimeError as e:
                _LOGGER.error("Nordigen API error: %s", str(e))
                if "expired" in str(e).lower():
                    errors["base"] = "requisition_expired"
                else:
                    errors["base"] = "api_error"
            except Exception as e:
                _LOGGER.exception("Unexpected error during setup: %s", str(e))
                errors["base"] = "unknown_error"

        # Show the input form again with error messages (if any)
        schema = vol.Schema(
            {
                vol.Required(CONF_SECRET_ID): str,
                vol.Required(CONF_SECRET_KEY): str,
                vol.Required(CONF_REQUISITION_ID): str,
                vol.Optional(CONF_REFRESH_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return NordigenAccountOptionsFlow(config_entry)


class NordigenAccountOptionsFlow(config_entries.OptionsFlow):
    """Handle updating config entry options for Nordigen Account."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options flow (requisition_id or refresh_token update)."""
        if user_input is not None:
            data = dict(self.config_entry.data)
            data[CONF_REQUISITION_ID] = user_input[CONF_REQUISITION_ID].strip()
            data[CONF_REFRESH_TOKEN] = user_input.get(CONF_REFRESH_TOKEN, "").strip()

            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})

        current_requisition_id = self.config_entry.data.get(CONF_REQUISITION_ID, "")
        current_refresh_token = self.config_entry.data.get(CONF_REFRESH_TOKEN, "")

        schema = vol.Schema(
            {
                vol.Required(CONF_REQUISITION_ID, default=current_requisition_id): str,
                vol.Optional(CONF_REFRESH_TOKEN, default=current_refresh_token): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
