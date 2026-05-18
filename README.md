# Buderus MX300 Home Assistant Integration

Experimental Home Assistant custom integration for Buderus/Bosch systems exposed through an MX300/K30 gateway and the MyBuderus PointT API.

## Status

- Works with the tested K30/MX300 gateway.
- Provides sensors, German and English entity names, selected controls, and selected numeric setpoints.
- Uses SingleKey Authorization Code + PKCE and stores a refresh token for automatic token renewal.
- Polls the Buderus/Bosch cloud API. The MX300 itself is only used as the cloud-connected gateway.

Confirmed writeable controls on the tested gateway:

- Extra hot water: `/dhwCircuits/dhw1/charge`
- DHW temperature reduction on alarm: `/dhwCircuits/dhw1/reduceTempOnAlarm`
- Heating circuit manual room setpoint: `/heatingCircuits/hc1/manualRoomSetpoint`
- Extra hot water duration: `/dhwCircuits/dhw1/chargeDuration`
- Extra hot water target temperature: `/dhwCircuits/dhw1/singleChargeSetpoint`

Confirmed read resources from the first MX300/K30 capture:

- `/system/info`
- `/system/sensors/temperatures/outdoor_t1`
- `/gateway/serialId`
- `/gateway/versionFirmware`
- `/gateway/versionHardware`
- `/heatingCircuits`
- `/dhwCircuits`
- `/heatSources/info`
- `/heatSources/chStatus`
- `/heatSources/actualSupplyTemperature`
- `/heatSources/returnTemperature`
- `/heatSources/numberOfStarts`
- `/heatSources/workingTime/totalSystem`
- `/notifications`

## Installation

1. Copy `custom_components/buderus_ha` to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to Settings -> Devices & services -> Add integration.
4. Search for `Buderus MX300`.
5. Follow the setup form.

## Initial Setup

The first SingleKey login currently works reliably only in a desktop browser. iPhone and Android are not recommended for the first setup when the MyBuderus app is installed, because the app can intercept the final `com.buderus.tt.dashtt://app/login` redirect before Home Assistant can use it.

No helper script is required. The setup form shows a SingleKey login URL and asks for the final redirect URL or authorization code.

Short version:

1. Open the browser developer tools with `F12` before logging in.
2. Open the `Network` tab and enable `Preserve log`.
3. Open the SingleKey login URL shown by Home Assistant.
4. Sign in.
5. A network or redirect error page after login is expected.
6. In the Network tab, open the last `/auth/connect/authorize/callback` request.
7. Copy the `Location` response header that starts with `com.buderus.tt.dashtt://app/login`.
8. Paste that URL into the Home Assistant setup form.

German step-by-step notes are in [docs/erste-einrichtung.md](docs/erste-einrichtung.md).

## Known Limitations

- This integration uses an observed, unofficial API. Buderus/Bosch can change endpoints, scopes, or payloads.
- SingleKey rejects normal HTTP callback URLs for the MyBuderus client, so Home Assistant cannot currently receive the redirect automatically.
- The tested SingleKey production server did not expose a working OAuth device-code endpoint for this client.
- Controls are intentionally limited to resources that reported `writeable: 1` on the tested gateway.
- Thermal disinfection is exposed as a diagnostic sensor only, because it was not confirmed as writeable.

## Development Notes

Local capture output, tokens, device identifiers, and probe data belong under `.analysis/`, which is ignored by Git. Do not commit that directory.
