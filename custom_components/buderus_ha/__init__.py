from __future__ import annotations

import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BuderusPointTClient
from .auth import BuderusOAuthClient
from .const import CONF_ACCESS_TOKEN, CONF_EXPIRES_AT, CONF_GATEWAY_ID, CONF_REFRESH_TOKEN, DOMAIN, PLATFORMS
from .coordinator import BuderusDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    oauth_client = BuderusOAuthClient(session)

    async def async_get_access_token() -> str:
        if time.time() < entry.data.get(CONF_EXPIRES_AT, 0) - 60:
            return entry.data[CONF_ACCESS_TOKEN]

        token_data = await oauth_client.refresh(entry.data[CONF_REFRESH_TOKEN])
        new_data = {
            **entry.data,
            CONF_ACCESS_TOKEN: token_data[CONF_ACCESS_TOKEN],
            CONF_EXPIRES_AT: token_data.get(CONF_EXPIRES_AT, entry.data.get(CONF_EXPIRES_AT, 0)),
        }
        if token_data.get(CONF_REFRESH_TOKEN):
            new_data[CONF_REFRESH_TOKEN] = token_data[CONF_REFRESH_TOKEN]
        hass.config_entries.async_update_entry(entry, data=new_data)
        return new_data[CONF_ACCESS_TOKEN]

    client = BuderusPointTClient(session, async_get_access_token)
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
