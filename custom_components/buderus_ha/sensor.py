from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BuderusDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BuderusSensorEntityDescription(SensorEntityDescription):
    resource_path: str
    value_key: str = "value"
    value_kind: str = "value"
    value_scale: float = 1.0


SENSOR_DESCRIPTIONS: tuple[BuderusSensorEntityDescription, ...] = (
    BuderusSensorEntityDescription(
        key="actual_supply_temperature",
        translation_key="actual_supply_temperature",
        resource_path="/heatSources/actualSupplyTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="return_temperature",
        translation_key="return_temperature",
        resource_path="/heatSources/returnTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        resource_path="/system/sensors/temperatures/outdoor_t1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="central_heating_status",
        translation_key="central_heating_status",
        resource_path="/heatSources/chStatus",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "on"],
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_operation_mode",
        translation_key="heating_circuit_operation_mode",
        resource_path="/heatingCircuits/hc1/operationMode",
        device_class=SensorDeviceClass.ENUM,
        options=["manual", "auto"],
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_overall_status",
        translation_key="heating_circuit_overall_status",
        resource_path="/heatingCircuits/hc1/overallStatus",
        device_class=SensorDeviceClass.ENUM,
        options=["ch_enabled", "ch_disabled"],
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_active_switch_program",
        translation_key="heating_circuit_active_switch_program",
        resource_path="/heatingCircuits/hc1/activeSwitchProgram",
        device_class=SensorDeviceClass.ENUM,
        options=["A", "B"],
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_current_room_setpoint",
        translation_key="heating_circuit_current_room_setpoint",
        resource_path="/heatingCircuits/hc1/currentRoomSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_manual_room_setpoint",
        translation_key="heating_circuit_manual_room_setpoint",
        resource_path="/heatingCircuits/hc1/manualRoomSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_summer_winter_mode",
        translation_key="heating_circuit_summer_winter_mode",
        resource_path="/heatingCircuits/hc1/currentSuWiMode",
        device_class=SensorDeviceClass.ENUM,
        options=["forced", "off", "cooling"],
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_heat_cool_mode",
        translation_key="heating_circuit_heat_cool_mode",
        resource_path="/heatingCircuits/hc1/heatCoolMode",
        device_class=SensorDeviceClass.ENUM,
        options=["heat", "cool", "heatCool"],
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_room_temperature",
        translation_key="heating_circuit_room_temperature",
        resource_path="/heatingCircuits/hc1/roomtemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_max_flow_temperature",
        translation_key="heating_circuit_max_flow_temperature",
        resource_path="/heatingCircuits/hc1/maxFlowTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_summer_winter_switch_mode",
        translation_key="heating_circuit_summer_winter_switch_mode",
        resource_path="/heatingCircuits/hc1/suWiSwitchMode",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "automatic", "forced"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_summer_winter_threshold",
        translation_key="heating_circuit_summer_winter_threshold",
        resource_path="/heatingCircuits/hc1/suWiThreshold",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="dhw_actual_temperature",
        translation_key="dhw_actual_temperature",
        resource_path="/dhwCircuits/dhw1/actualTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="dhw_current_setpoint",
        translation_key="dhw_current_setpoint",
        resource_path="/dhwCircuits/dhw1/currentSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="dhw_operation_mode",
        translation_key="dhw_operation_mode",
        resource_path="/dhwCircuits/dhw1/operationMode",
        device_class=SensorDeviceClass.ENUM,
        options=["Off", "low", "high", "ownprogram", "eco"],
    ),
    BuderusSensorEntityDescription(
        key="dhw_overall_status",
        translation_key="dhw_overall_status",
        resource_path="/dhwCircuits/dhw1/overallStatus",
        device_class=SensorDeviceClass.ENUM,
        options=["dhw_enabled", "dhw_disabled"],
    ),
    BuderusSensorEntityDescription(
        key="dhw_charge",
        translation_key="dhw_charge",
        resource_path="/dhwCircuits/dhw1/charge",
        device_class=SensorDeviceClass.ENUM,
        options=["start", "stop"],
    ),
    BuderusSensorEntityDescription(
        key="dhw_charge_duration",
        translation_key="dhw_charge_duration",
        resource_path="/dhwCircuits/dhw1/chargeDuration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="dhw_single_charge_setpoint",
        translation_key="dhw_single_charge_setpoint",
        resource_path="/dhwCircuits/dhw1/singleChargeSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="dhw_reduce_temperature_on_alarm",
        translation_key="dhw_reduce_temperature_on_alarm",
        resource_path="/dhwCircuits/dhw1/reduceTempOnAlarm",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "on"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="dhw_thermal_disinfection_mode",
        translation_key="dhw_thermal_disinfection_mode",
        resource_path="/dhwCircuits/dhw1/tdMode",
        device_class=SensorDeviceClass.ENUM,
        options=["on", "off"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="actual_heat_demand",
        translation_key="actual_heat_demand",
        resource_path="/heatSources/actualHeatDemand",
        value_kind="values_non_empty_join",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "none",
            "ch",
            "dhw",
            "frost",
            "ch, dhw",
            "ch, frost",
            "dhw, frost",
            "ch, dhw, frost",
        ],
    ),
    BuderusSensorEntityDescription(
        key="actual_modulation",
        translation_key="actual_modulation",
        resource_path="/heatSources/actualModulation",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="compressor_status",
        translation_key="compressor_status",
        resource_path="/heatSources/compressor/status",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "heating", "cooling", "dhw", "pool", "pool_heat", "defrost", "alarm"],
    ),
    BuderusSensorEntityDescription(
        key="electric_heater_status",
        translation_key="electric_heater_status",
        resource_path="/heatSources/Source/eHeater/status",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "heating", "dhw", "pool", "pool_heat", "alarm"],
    ),
    BuderusSensorEntityDescription(
        key="number_of_starts",
        translation_key="number_of_starts",
        resource_path="/heatSources/numberOfStarts",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BuderusSensorEntityDescription(
        key="number_of_starts_heating",
        translation_key="number_of_starts_heating",
        resource_path="/heatSources/hs1/numberOfStarts",
        value_key="ch",
        value_kind="values_dict_key",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BuderusSensorEntityDescription(
        key="number_of_starts_dhw",
        translation_key="number_of_starts_dhw",
        resource_path="/heatSources/hs1/numberOfStarts",
        value_key="dhw",
        value_kind="values_dict_key",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BuderusSensorEntityDescription(
        key="number_of_starts_cooling",
        translation_key="number_of_starts_cooling",
        resource_path="/heatSources/hs1/numberOfStarts",
        value_key="cooling",
        value_kind="values_dict_key",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="total_system_working_time",
        translation_key="total_system_working_time",
        resource_path="/heatSources/workingTime/totalSystem",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_scale=1 / 3600,
        suggested_display_precision=1,
    ),
    BuderusSensorEntityDescription(
        key="notification_count",
        translation_key="notification_count",
        resource_path="/notifications",
        value_kind="values_length",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BuderusSensorEntityDescription(
        key="heat_pump_type",
        translation_key="heat_pump_type",
        resource_path="/heatSources/hs1/heatPumpType",
        device_class=SensorDeviceClass.ENUM,
        options=["air_water", "liquid_water", "exhaustAir_water"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="heat_source_type",
        translation_key="heat_source_type",
        resource_path="/heatSources/hs1/type",
        device_class=SensorDeviceClass.ENUM,
        options=["No_Appliance", "OilBoiler", "GasBoiler", "Heatpump", "unknownBoiler", "eBoiler"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_heating_type",
        translation_key="heating_circuit_heating_type",
        resource_path="/heatingCircuits/hc1/heatingType",
        device_class=SensorDeviceClass.ENUM,
        options=["radiator", "convector", "floor"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_control_type",
        translation_key="heating_circuit_control_type",
        resource_path="/heatingCircuits/hc1/controlType",
        device_class=SensorDeviceClass.ENUM,
        options=["wdcoptimized", "wdcsimplified"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="heating_circuit_switch_program_mode",
        translation_key="heating_circuit_switch_program_mode",
        resource_path="/heatingCircuits/hc1/switchProgramMode",
        device_class=SensorDeviceClass.ENUM,
        options=["level"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="gateway_data_processing_status",
        translation_key="gateway_data_processing_status",
        resource_path="/gateway/dataProcessing/status",
        device_class=SensorDeviceClass.ENUM,
        options=["in_progress", "completed"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="gateway_timezone",
        translation_key="gateway_timezone",
        resource_path="/gateway/tzInfo/timeZone",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="system_brand",
        translation_key="system_brand",
        resource_path="/system/brand",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="system_bus",
        translation_key="system_bus",
        resource_path="/system/bus",
        device_class=SensorDeviceClass.ENUM,
        options=["No_Bus", "Detecting", "EMS2_0"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="system_country",
        translation_key="system_country",
        resource_path="/system/country",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="global_season_optimizer_mode",
        translation_key="global_season_optimizer_mode",
        resource_path="/system/globalSeasonOptimizer/currentMode",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "heating", "cooling"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BuderusSensorEntityDescription(
        key="isrc_support_status",
        translation_key="isrc_support_status",
        resource_path="/system/iSRC/supportStatus",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "NOT_SUPPORTED_INCOMPATIBLE_CONTROLLER",
            "NOT_SUPPORTED_PAIRING_ENABLED",
            "SUPPORTED",
            "IN_EVALUATION",
        ],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BuderusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BuderusSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BuderusSensor(CoordinatorEntity[BuderusDataUpdateCoordinator], SensorEntity):
    entity_description: BuderusSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BuderusDataUpdateCoordinator,
        description: BuderusSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.gateway_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        resource = self.coordinator.data["resources"].get(self.entity_description.resource_path)
        if not resource:
            return None

        if self.entity_description.value_kind == "values_length":
            return len(resource.get("values") or [])

        if self.entity_description.value_kind == "values_non_empty_join":
            values = [str(value) for value in resource.get("values") or [] if value not in ("", None)]
            return ", ".join(values) if values else "none"

        if self.entity_description.value_kind == "values_dict_key":
            for item in resource.get("values") or []:
                if isinstance(item, dict) and self.entity_description.value_key in item:
                    return item[self.entity_description.value_key]
            return None

        value = resource.get(self.entity_description.value_key)
        if value in (32767.0, -32768.0):
            return None
        if isinstance(value, (int, float)) and self.entity_description.value_scale != 1.0:
            return value * self.entity_description.value_scale
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        resource = self.coordinator.data["resources"].get(self.entity_description.resource_path)
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
