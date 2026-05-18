from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BuderusApiError, BuderusAuthError, BuderusPointTClient
from .auth import (
    BuderusOAuthClient,
    build_authorization_url,
    create_code_verifier,
    create_state,
    parse_authorization_response,
)
from .const import CONF_ACCESS_TOKEN, CONF_EXPIRES_AT, CONF_GATEWAY_ID, CONF_REFRESH_TOKEN, DOMAIN


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("redirect_url"): str,
        vol.Optional(CONF_GATEWAY_ID): str,
    }
)


async def validate_input(
    hass: HomeAssistant,
    token_data: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, str]:
    session = async_get_clientsession(hass)
    client = BuderusPointTClient(session, token_data[CONF_ACCESS_TOKEN])

    gateway_id = data.get(CONF_GATEWAY_ID)
    if not gateway_id:
        gateways = await client.get_gateways()
        if not gateways:
            raise BuderusApiError("No gateways found")
        gateway_id = str(gateways[0]["deviceId"])

    gateway = await client.get_gateway(gateway_id)
    await client.get_resource(gateway_id, "/system/info")

    title = f"Buderus {gateway.get('deviceType', 'gateway')} {gateway_id}"
    return {"gateway_id": gateway_id, "title": title}


class BuderusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Buderus MX300 integration."""

    VERSION = 1
    _authorization_url: str
    _code_verifier: str
    _state: str

    def _ensure_authorization_context(self) -> None:
        if hasattr(self, "_authorization_url"):
            return
        self._code_verifier = create_code_verifier()
        self._state = create_state()
        self._authorization_url = build_authorization_url(self._code_verifier, self._state)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        self._ensure_authorization_context()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                code = parse_authorization_response(user_input["redirect_url"], self._state)
                session = async_get_clientsession(self.hass)
                token_data = await BuderusOAuthClient(session).exchange_code(code, self._code_verifier)
                if not token_data.get(CONF_REFRESH_TOKEN):
                    raise BuderusAuthError("Token response did not include a refresh token")
                info = await validate_input(self.hass, token_data, user_input)
            except BuderusAuthError:
                errors["base"] = "invalid_auth"
            except BuderusApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["gateway_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_ACCESS_TOKEN: token_data[CONF_ACCESS_TOKEN],
                        CONF_REFRESH_TOKEN: token_data[CONF_REFRESH_TOKEN],
                        CONF_EXPIRES_AT: token_data.get(CONF_EXPIRES_AT, 0),
                        CONF_GATEWAY_ID: info["gateway_id"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"authorization_url": self._authorization_url},
        )
