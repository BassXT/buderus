"""Config flow for the Buderus MX300 integration."""

from __future__ import annotations

from collections.abc import Mapping
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
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_GATEWAY_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("redirect_url"): str,
        vol.Optional(CONF_GATEWAY_ID): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("redirect_url"): str,
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
    _reauth_entry: config_entries.ConfigEntry | None = None

    def _ensure_authorization_context(self) -> None:
        if hasattr(self, "_authorization_url"):
            return
        self._code_verifier = create_code_verifier()
        self._state = create_state()
        self._authorization_url = build_authorization_url(
            self._code_verifier, self._state
        )

    def _reset_authorization_context(self) -> None:
        """Verwirft den bisherigen PKCE-Kontext.

        Noetig beim Reauth: state und code_verifier der urspruenglichen
        Einrichtung sind laengst verbraucht bzw. gar nicht mehr im Speicher,
        also muss ein frisches Paar erzeugt werden.
        """
        for attr in ("_authorization_url", "_code_verifier", "_state"):
            if hasattr(self, attr):
                delattr(self, attr)
        self._ensure_authorization_context()

    async def _async_exchange(self, redirect_url: str) -> dict[str, Any]:
        """Redirect-URL -> Tokenpaar. Wirft BuderusAuthError/BuderusApiError."""
        code = parse_authorization_response(redirect_url, self._state)
        session = async_get_clientsession(self.hass)
        token_data = await BuderusOAuthClient(session).exchange_code(
            code, self._code_verifier
        )
        if not token_data.get(CONF_REFRESH_TOKEN):
            raise BuderusAuthError("Token response did not include a refresh token")
        return token_data

    # --- Ersteinrichtung -------------------------------------------------

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        self._ensure_authorization_context()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                token_data = await self._async_exchange(user_input["redirect_url"])
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

    # --- Reauth ----------------------------------------------------------

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Wird aufgerufen, wenn die Integration ConfigEntryAuthFailed wirft."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        # Frischer PKCE-Kontext: der alte state/verifier ist verbraucht.
        self._reset_authorization_context()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        assert self._reauth_entry is not None
        errors: dict[str, str] = {}
        gateway_id = self._reauth_entry.data[CONF_GATEWAY_ID]

        if user_input is not None:
            try:
                token_data = await self._async_exchange(user_input["redirect_url"])
                # Gegen die *bestehende* Gateway-ID pruefen, damit sich nicht
                # versehentlich ein anderer Account in diesen Entry schreibt.
                info = await validate_input(
                    self.hass, token_data, {CONF_GATEWAY_ID: gateway_id}
                )
            except BuderusAuthError:
                errors["base"] = "invalid_auth"
            except BuderusApiError:
                errors["base"] = "cannot_connect"
            else:
                if info["gateway_id"] != gateway_id:
                    return self.async_abort(reason="wrong_account")

                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_ACCESS_TOKEN: token_data[CONF_ACCESS_TOKEN],
                        CONF_REFRESH_TOKEN: token_data[CONF_REFRESH_TOKEN],
                        CONF_EXPIRES_AT: token_data.get(CONF_EXPIRES_AT, 0),
                    },
                )
                await self.hass.config_entries.async_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")

            # Nach einem Fehlversuch ist der Code verbrannt -> neue URL,
            # sonst laeuft der zweite Versuch garantiert wieder ins Leere.
            self._reset_authorization_context()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "authorization_url": self._authorization_url,
                "gateway_id": gateway_id,
            },
        )
