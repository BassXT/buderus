from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
TOKEN_URL = "https://singlekey-id.com/auth/connect/token"
POINTT_BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1"
USER_AGENT = "DashApp/3.7.0 (iOS-Release)"

TOKEN_FILE = Path(".analysis/auth/tokens.json")
OUT_DIR = Path(".analysis/pointt_candidates")

RESOURCE_PATHS = (
    "/gateway/DateTime",
    "/gateway/dataProcessing/status",
    "/gateway/tzInfo/timeZone",
    "/gateway/uuid",
    "/gateway/wifi/mac",
    "/gateway/wifi/ssid",
    "/system/appliance",
    "/system/appliance/enabled",
    "/system/appliance/model",
    "/system/appliance/versionFirmware",
    "/system/awayMode/enabled",
    "/system/brand",
    "/system/bus",
    "/system/country",
    "/system/globalSeasonOptimizer/currentMode",
    "/system/holidayMode",
    "/system/iSRC/supportStatus",
    "/system/lowNoise/duration",
    "/system/lowNoise/mode",
    "/system/systemOfUnits",
    "/system/variableTariff/supportStatus",
    "/system/variableTariff/priceInfo",
    "/system/variableTariff/currentPriceCatagorization",
    "/system/variableTariff/ch/status",
    "/system/variableTariff/ch/currentSetpoint",
    "/system/variableTariff/dhw/status",
    "/system/variableTariff/dhw/currentOpmode",
    "/heatingCircuits/hc1",
    "/heatingCircuits/hc1/activeSwitchProgram",
    "/heatingCircuits/hc1/operationMode",
    "/heatingCircuits/hc1/heatCurve",
    "/heatingCircuits/hc1/maxFlowTemp",
    "/heatingCircuits/hc1/overallStatus",
    "/heatingCircuits/hc1/roomTempOffset",
    "/heatingCircuits/hc1/suWiSwitchMode",
    "/heatingCircuits/hc1/suWiThreshold",
    "/heatingCircuits/hc1/switchPrograms",
    "/heatingCircuits/hc1/currentRoomSetpoint",
    "/heatingCircuits/hc1/currentSetpoint",
    "/heatingCircuits/hc1/manualRoomSetpoint",
    "/heatingCircuits/hc1/temporaryRoomSetpoint",
    "/heatingCircuits/hc1/currentTemperatureLevel",
    "/heatingCircuits/hc1/currentSuWiMode",
    "/heatingCircuits/hc1/heatCoolMode",
    "/heatingCircuits/hc1/heatingType",
    "/heatingCircuits/hc1/controlType",
    "/heatingCircuits/hc1/roomtemperature",
    "/heatingCircuits/hc1/switchProgramMode",
    "/heatingCircuits/hc1/temperatureLevels/eco",
    "/heatingCircuits/hc1/temperatureLevels/comfort2",
    "/heatingCircuits/hc1/switchPrograms/A",
    "/heatingCircuits/hc1/switchPrograms/B",
    "/heatingCircuits/hc1/cooling/operationMode",
    "/heatingCircuits/hc1/cooling/roomTempSetpoint",
    "/dhwCircuits/dhw1",
    "/dhwCircuits/dhw1/actualTemp",
    "/dhwCircuits/dhw1/charge",
    "/dhwCircuits/dhw1/chargeDuration",
    "/dhwCircuits/dhw1/currentSetpoint",
    "/dhwCircuits/dhw1/ecoStop",
    "/dhwCircuits/dhw1/highStop",
    "/dhwCircuits/dhw1/lowStop",
    "/dhwCircuits/dhw1/currentFriwaSupplyTemperature",
    "/dhwCircuits/dhw1/inletTemperature",
    "/dhwCircuits/dhw1/manualsetpoint",
    "/dhwCircuits/dhw1/monitorValues",
    "/dhwCircuits/dhw1/numberOfShowersAvailable",
    "/dhwCircuits/dhw1/operationMode",
    "/dhwCircuits/dhw1/operationSetpoints",
    "/dhwCircuits/dhw1/overallStatus",
    "/dhwCircuits/dhw1/outletTemperature",
    "/dhwCircuits/dhw1/outTemp",
    "/dhwCircuits/dhw1/recirculation/enabled",
    "/dhwCircuits/dhw1/reduceTempOnAlarm",
    "/dhwCircuits/dhw1/safetyTemperature",
    "/dhwCircuits/dhw1/singleChargeSetpoint",
    "/dhwCircuits/dhw1/tdMode",
    "/dhwCircuits/dhw1/tdmaxDuration",
    "/dhwCircuits/dhw1/tdrunningStatus",
    "/dhwCircuits/dhw1/tdsetPoint",
    "/dhwCircuits/dhw1/tdwarmKeepingTime",
    "/dhwCircuits/dhw1/temperatureLevels",
    "/dhwCircuits/dhw1/volumeFlow",
    "/dhwCircuits/dhw1/waterTotalConsumption",
    "/heatSources/actualHeatDemand",
    "/heatSources/actualModulation",
    "/heatSources/compressor/status",
    "/heatSources/electricityTotalConsumption",
    "/heatSources/gasTotalConsumption",
    "/heatSources/hs1/actualPower",
    "/heatSources/hs1/brineCircuit/collectorInflowTemp",
    "/heatSources/hs1/brineCircuit/collectorOutflowTemp",
    "/heatSources/hs1/electricityTotalConsumption",
    "/heatSources/hs1/heatPumpType",
    "/heatSources/hs1/numberOfStarts",
    "/heatSources/hs1/operationHours",
    "/heatSources/hs1/powerPercentage",
    "/heatSources/hs1/type",
    "/heatSources/hs2/defrostActive",
    "/heatSources/hs2/numberOfStarts",
    "/heatSources/passiveCooling/inflowTemp",
    "/heatSources/pvContactState",
    "/heatSources/Source/eHeater/status",
    "/heatSources/systemPressure",
    "/heatSources/systemPressureRange",
)


def request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, data: bytes | None = None) -> object:
    request = Request(url, headers=headers or {}, data=data, method=method)
    with urlopen(request, timeout=30) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else None


def refresh_token(token_data: dict) -> dict:
    payload = urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": token_data["refresh_token"],
        }
    ).encode()
    refreshed = request_json(
        TOKEN_URL,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
        data=payload,
    )
    if not isinstance(refreshed, dict) or "access_token" not in refreshed:
        raise SystemExit("Refresh response did not include an access token")

    refreshed["expires_at"] = int(time.time()) + int(refreshed.get("expires_in", 0))
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = token_data["refresh_token"]
    TOKEN_FILE.write_text(json.dumps(refreshed, indent=2), encoding="utf-8")
    return refreshed


def resource_file_name(path: str) -> str:
    return path.strip("/").replace("/", "__").replace("?", "_").replace("=", "_") + ".json"


def main() -> None:
    token_data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    if time.time() >= int(token_data.get("expires_at", 0)) - 60:
        token_data = refresh_token(token_data)

    access_token = token_data["access_token"]
    gateways = request_json(
        f"{POINTT_BASE_URL}/gateways/",
        headers={"Accept": "application/json", "Authorization": f"Bearer {access_token}", "User-Agent": USER_AGENT},
    )
    gateway = gateways[0] if isinstance(gateways, list) else gateways
    gateway_id = str(gateway["deviceId"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for path in RESOURCE_PATHS:
        url = f"{POINTT_BASE_URL}/gateways/{gateway_id}/resource/{path.strip('/')}"
        try:
            data = request_json(
                url,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept-Charset": "UTF-8",
                    "User-Agent": USER_AGENT,
                },
            )
        except HTTPError as err:
            failures.append({"path": path, "status": err.code})
            continue
        except (URLError, TimeoutError) as err:
            failures.append({"path": path, "error": str(err)})
            continue

        (OUT_DIR / resource_file_name(path)).write_text(json.dumps(data, indent=2), encoding="utf-8")
        summary = {"path": path}
        if isinstance(data, dict):
            summary["type"] = data.get("type")
            summary["writeable"] = data.get("writeable")
            if "value" in data:
                summary["value"] = data.get("value")
            if "values" in data:
                summary["values_count"] = len(data.get("values") or [])
            if "references" in data:
                summary["references_count"] = len(data.get("references") or [])
        successes.append(summary)

    (OUT_DIR / "_successes.json").write_text(json.dumps(successes, indent=2), encoding="utf-8")
    (OUT_DIR / "_failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")

    print(f"Successful resources: {len(successes)}")
    print(f"Failed resources: {len(failures)}")
    print(f"Results written to {OUT_DIR}")
    for item in successes:
        print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
