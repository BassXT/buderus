from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BuderusPointTClient
from .auth import BuderusOAuthClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_GATEWAY_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BuderusDataUpdateCoordinator

LOGGER = logging.getLogger(__name__)

# Puffer vor dem Ablauf. 60 s sind bei langsamen Requests und leichtem
# Uhren-Versatz zwischen Client und Server zu knapp.
TOKEN_EXPIRY_MARGIN = 300


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    oauth_client = BuderusOAuthClient(session)

    # Serialisiert den Refresh. Ohne diesen Lock koennen Haupt- und
    # EMON-Coordinator gleichzeitig refreshen; da SingleKey ID die
    # Refresh-Tokens rotiert, laeuft der zweite Aufruf in invalid_grant.
    token_lock = asyncio.Lock()

    async def _refresh_token() -> str:
        """Erneuert den Token. Muss unter token_lock aufgerufen werden."""
        try:
            token_data = await oauth_client.refresh(entry.data[CONF_REFRESH_TOKEN])
        except Exception as err:  # noqa: BLE001
            # Kein stiller Tod: HA soll den Reauth-Flow anbieten.
            raise ConfigEntryAuthFailed(f"Token-Refresh fehlgeschlagen: {err}") from err

        new_data = {
            **entry.data,
            CONF_ACCESS_TOKEN: token_data[CONF_ACCESS_TOKEN],
            CONF_EXPIRES_AT: token_data.get(
                CONF_EXPIRES_AT, entry.data.get(CONF_EXPIRES_AT, 0)
            ),
        }
        if token_data.get(CONF_REFRESH_TOKEN):
            new_data[CONF_REFRESH_TOKEN] = token_data[CONF_REFRESH_TOKEN]

        hass.config_entries.async_update_entry(entry, data=new_data)
        LOGGER.debug(
            "Access-Token erneuert, gueltig bis %s",
            new_data.get(CONF_EXPIRES_AT),
        )
        return new_data[CONF_ACCESS_TOKEN]

    async def async_get_access_token() -> str:
        # Schnellpfad ohne Lock: Token ist sicher gueltig.
        if time.time() < entry.data.get(CONF_EXPIRES_AT, 0) - TOKEN_EXPIRY_MARGIN:
            return entry.data[CONF_ACCESS_TOKEN]

        async with token_lock:
            # Zweite Pruefung *innerhalb* des Locks: Wer hier wartend
            # ankommt, findet den Token oft schon erneuert vor.
            if time.time() < entry.data.get(CONF_EXPIRES_AT, 0) - TOKEN_EXPIRY_MARGIN:
                return entry.data[CONF_ACCESS_TOKEN]
            return await _refresh_token()

    async def async_force_refresh() -> str:
        """Erzwingt einen Refresh, z. B. nach einem 401 trotz gueltiger Laufzeit."""
        async with token_lock:
            return await _refresh_token()

    client = BuderusPointTClient(
        session,
        async_get_access_token,
        token_refresh=async_force_refresh,
    )
    coordinator = BuderusDataUpdateCoordinator(
        hass,
        client,
        entry.data[CONF_GATEWAY_ID],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
