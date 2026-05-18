from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BuderusDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BuderusNumberEntityDescription(NumberEntityDescription):
    resource_path: str
    value_key: str = "value"


NUMBER_DESCRIPTIONS: tuple[BuderusNumberEntityDescription, ...] = (
    BuderusNumberEntityDescription(
        key="heating_circuit_manual_room_setpoint",
        translation_key="heating_circuit_manual_room_setpoint",
        resource_path="/heatingCircuits/hc1/manualRoomSetpoint",
        native_min_value=5,
        native_max_value=30,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
    ),
    BuderusNumberEntityDescription(
        key="dhw_charge_duration",
        translation_key="dhw_charge_duration",
        resource_path="/dhwCircuits/dhw1/chargeDuration",
        native_min_value=15,
        native_max_value=2880,
        native_step=15,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    BuderusNumberEntityDescription(
        key="dhw_single_charge_setpoint",
        translation_key="dhw_single_charge_setpoint",
        resource_path="/dhwCircuits/dhw1/singleChargeSetpoint",
        native_min_value=50,
        native_max_value=70,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
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
        BuderusNumber(coordinator, description)
        for description in NUMBER_DESCRIPTIONS
        if _resource_is_writeable(coordinator, description.resource_path)
    )


def _resource_is_writeable(
    coordinator: BuderusDataUpdateCoordinator,
    resource_path: str,
) -> bool:
    resource = coordinator.data["resources"].get(resource_path)
    return resource is not None and resource.get("writeable") == 1


class BuderusNumber(CoordinatorEntity[BuderusDataUpdateCoordinator], NumberEntity):
    entity_description: BuderusNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BuderusDataUpdateCoordinator,
        description: BuderusNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.gateway_id}_{description.key}_number"

    @property
    def native_value(self) -> float | None:
        resource = self._resource
        if not resource:
            return None
        value = resource.get(self.entity_description.value_key)
        if value in (None, 32767.0, -32768.0):
            return None
        return float(value)

    @property
    def native_min_value(self) -> float:
        resource = self._resource or {}
        return float(resource.get("minValue", self.entity_description.native_min_value))

    @property
    def native_max_value(self) -> float:
        resource = self._resource or {}
        return float(resource.get("maxValue", self.entity_description.native_max_value))

    async def async_set_native_value(self, value: float) -> None:
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
