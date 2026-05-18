from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BuderusApiError, BuderusPointTClient
from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

RESOURCE_PATHS: tuple[str, ...] = (
    "/system/info",
    "/system/sensors/temperatures/outdoor_t1",
    "/gateway/serialId",
    "/gateway/dataProcessing/status",
    "/gateway/tzInfo/timeZone",
    "/gateway/uuid",
    "/gateway/wifi/mac",
    "/gateway/versionFirmware",
    "/gateway/versionHardware",
    "/heatingCircuits",
    "/heatingCircuits/hc1/activeSwitchProgram",
    "/heatingCircuits/hc1/operationMode",
    "/heatingCircuits/hc1/currentRoomSetpoint",
    "/heatingCircuits/hc1/manualRoomSetpoint",
    "/heatingCircuits/hc1/currentSuWiMode",
    "/heatingCircuits/hc1/heatCoolMode",
    "/heatingCircuits/hc1/heatingType",
    "/heatingCircuits/hc1/controlType",
    "/heatingCircuits/hc1/maxFlowTemp",
    "/heatingCircuits/hc1/overallStatus",
    "/heatingCircuits/hc1/roomtemperature",
    "/heatingCircuits/hc1/suWiSwitchMode",
    "/heatingCircuits/hc1/suWiThreshold",
    "/heatingCircuits/hc1/switchProgramMode",
    "/dhwCircuits",
    "/dhwCircuits/dhw1/actualTemp",
    "/dhwCircuits/dhw1/charge",
    "/dhwCircuits/dhw1/chargeDuration",
    "/dhwCircuits/dhw1/currentSetpoint",
    "/dhwCircuits/dhw1/operationMode",
    "/dhwCircuits/dhw1/overallStatus",
    "/dhwCircuits/dhw1/reduceTempOnAlarm",
    "/dhwCircuits/dhw1/singleChargeSetpoint",
    "/dhwCircuits/dhw1/tdMode",
    "/heatSources/info",
    "/heatSources/actualHeatDemand",
    "/heatSources/actualModulation",
    "/heatSources/chStatus",
    "/heatSources/compressor/status",
    "/heatSources/actualSupplyTemperature",
    "/heatSources/returnTemperature",
    "/heatSources/numberOfStarts",
    "/heatSources/hs1/heatPumpType",
    "/heatSources/hs1/numberOfStarts",
    "/heatSources/hs1/type",
    "/heatSources/Source/eHeater/status",
    "/heatSources/workingTime/totalSystem",
    "/system/brand",
    "/system/bus",
    "/system/country",
    "/system/globalSeasonOptimizer/currentMode",
    "/system/iSRC/supportStatus",
    "/notifications",
)


class BuderusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch all currently known read-only PointT resources."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BuderusPointTClient,
        gateway_id: str,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.client = client
        self.gateway_id = gateway_id

    async def _async_update_data(self) -> dict[str, Any]:
        resources: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}

        try:
            gateway = await self.client.get_gateway(self.gateway_id)
            partnumber = await self.client.get_partnumber(self.gateway_id)
        except BuderusApiError as err:
            raise UpdateFailed(str(err)) from err

        for path in RESOURCE_PATHS:
            try:
                resources[path] = await self.client.get_resource(self.gateway_id, path)
            except BuderusApiError as err:
                errors[path] = str(err)
                LOGGER.debug("Failed to fetch %s: %s", path, err)

        if not resources:
            raise UpdateFailed("No Buderus resources could be fetched")

        return {
            "gateway": gateway,
            "partnumber": partnumber,
            "resources": resources,
            "errors": errors,
        }
