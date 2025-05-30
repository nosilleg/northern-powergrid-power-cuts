"""Config flow for Northern Powergrid Power Cuts integration."""

import logging

import aiohttp
import async_timeout
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_ENDPOINT,
    CONF_NAME,
    CONF_POSTCODE,
    DEFAULT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

MIN_POSTCODE_LENGTH = 5
MAX_POSTCODE_LENGTH = 7
HTTP_OK = 200


class NorthernPowergridFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Northern Powergrid Power Cuts."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate postcode format (basic validation)
            postcode = user_input[CONF_POSTCODE].upper().replace(" ", "")
            if (
                len(postcode) < MIN_POSTCODE_LENGTH
                or len(postcode) > MAX_POSTCODE_LENGTH
            ):
                errors[CONF_POSTCODE] = "invalid_postcode"
            else:
                # Test connection to API
                try:
                    session = async_get_clientsession(self.hass)
                    with async_timeout.timeout(10):
                        response = await session.get(API_ENDPOINT)
                        if response.status != HTTP_OK:
                            errors["base"] = "cannot_connect"
                except (aiohttp.ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"

                if not errors:
                    # Create entry
                    await self.async_set_unique_id(postcode)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Northern Powergrid {user_input[CONF_POSTCODE]}",
                        data=user_input,
                    )

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POSTCODE): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                },
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NorthernPowergridOptionsFlowHandler(config_entry)


class NorthernPowergridOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POSTCODE,
                        default=self.config_entry.data.get(CONF_POSTCODE),
                    ): str,
                    vol.Optional(
                        CONF_NAME,
                        default=self.config_entry.data.get(CONF_NAME, DEFAULT_NAME),
                    ): str,
                },
            ),
        )
