from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BuderusDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BuderusSwitchEntityDescription(SwitchEntityDescription):
    resource_path: str
    on_value: str
    off_value: str
    value_key: str = "value"


SWITCH_DESCRIPTIONS: tuple[BuderusSwitchEntityDescription, ...] = (
    BuderusSwitchEntityDescription(
        key="dhw_charge",
        translation_key="dhw_charge",
        resource_path="/dhwCircuits/dhw1/charge",
        on_value="start",
        off_value="stop",
    ),
    BuderusSwitchEntityDescription(
        key="dhw_reduce_temperature_on_alarm",
        translation_key="dhw_reduce_temperature_on_alarm",
        resource_path="/dhwCircuits/dhw1/reduceTempOnAlarm",
        on_value="on",
        off_value="off",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BuderusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BuderusSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
        if _resource_is_writeable(coordinator, description.resource_path)
    )


def _resource_is_writeable(
    coordinator: BuderusDataUpdateCoordinator,
    resource_path: str,
) -> bool:
    resource = coordinator.data["resources"].get(resource_path)
    return resource is not None and resource.get("writeable") == 1


class BuderusSwitch(CoordinatorEntity[BuderusDataUpdateCoordinator], SwitchEntity):
    entity_description: BuderusSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BuderusDataUpdateCoordinator,
        description: BuderusSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.gateway_id}_{description.key}_switch"

    @property
    def is_on(self) -> bool | None:
        resource = self._resource
        if not resource:
            return None
        return resource.get(self.entity_description.value_key) == self.entity_description.on_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_value(self.entity_description.on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_value(self.entity_description.off_value)

    async def _async_set_value(self, value: str) -> None:
        resource = self._resource or {}
        await self.coordinator.client.set_resource_value(
            self.coordinator.gateway_id,
            self.entity_description.resource_path,
            value,
            resource_type=resource.get("type"),
        )
        await self.coordinator.async_request_refresh()

    @property
    def _resource(self) -> dict[str, Any] | None:
        return self.coordinator.data["resources"].get(self.entity_description.resource_path)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        resource = self._resource
        if not resource:
            return None
        return {
            "resource_id": resource.get("id"),
            "resource_type": resource.get("type"),
            "writeable": resource.get("writeable"),
        }

    @property
    def device_info(self) -> dict[str, Any]:
        gateway = self.coordinator.data.get("gateway", {})
        partnumber = self.coordinator.data.get("partnumber", {})
        resources = self.coordinator.data.get("resources", {})

        firmware = resources.get("/gateway/versionFirmware", {}).get("value") or gateway.get("firmwareVersion")
        hardware = resources.get("/gateway/versionHardware", {}).get("value") or gateway.get("hardwareVersion")

        return {
            "identifiers": {(DOMAIN, self.coordinator.gateway_id)},
            "manufacturer": "Buderus/Bosch",
            "model": f"{gateway.get('deviceType')} {partnumber.get('partNumber')}".strip(),
            "name": f"Buderus Gateway {self.coordinator.gateway_id}",
            "sw_version": firmware,
            "hw_version": hardware,
            "serial_number": resources.get("/gateway/serialId", {}).get("value"),
        }
