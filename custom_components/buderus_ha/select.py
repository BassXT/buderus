from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BuderusDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BuderusSelectEntityDescription(SelectEntityDescription):
    resource_path: str
    options: tuple[str, ...]
    option_to_value: dict[str, str]
    value_key: str = "value"


SELECT_DESCRIPTIONS: tuple[BuderusSelectEntityDescription, ...] = (
    BuderusSelectEntityDescription(
        key="dhw_operation_mode",
        translation_key="dhw_operation_mode",
        resource_path="/dhwCircuits/dhw1/operationMode",
        options=("off", "low", "eco", "high", "ownprogram"),
        option_to_value={
            "off": "Off",
            "low": "low",
            "eco": "eco",
            "high": "high",
            "ownprogram": "ownprogram",
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BuderusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BuderusSelect(coordinator, description)
        for description in SELECT_DESCRIPTIONS
        if _resource_is_writeable(coordinator, description.resource_path)
    )


def _resource_is_writeable(
    coordinator: BuderusDataUpdateCoordinator,
    resource_path: str,
) -> bool:
    resource = coordinator.data["resources"].get(resource_path)
    return resource is not None and resource.get("writeable") == 1


class BuderusSelect(CoordinatorEntity[BuderusDataUpdateCoordinator], SelectEntity):
    entity_description: BuderusSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BuderusDataUpdateCoordinator,
        description: BuderusSelectEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.gateway_id}_{description.key}_select"

    @property
    def options(self) -> list[str]:
        return list(self.entity_description.options)

    @property
    def current_option(self) -> str | None:
        resource = self._resource
        if not resource:
            return None

        value = resource.get(self.entity_description.value_key)
        if value is None:
            return None

        option = self._value_to_option(str(value))
        return option if option in self.entity_description.options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.entity_description.option_to_value:
            raise ValueError(f"Unsupported option: {option}")

        resource = self._resource or {}
        await self.coordinator.client.set_resource_value(
            self.coordinator.gateway_id,
            self.entity_description.resource_path,
            self.entity_description.option_to_value[option],
            resource_type=resource.get("type"),
        )
        await self.coordinator.async_request_refresh()

    def _value_to_option(self, value: str) -> str:
        for option, api_value in self.entity_description.option_to_value.items():
            if value == api_value or value.lower() == api_value.lower():
                return option
        return value.lower()

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
