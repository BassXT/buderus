# Buderus MX300 Home Assistant Integration

Experimental Home Assistant custom integration for Buderus/Bosch systems exposed through an MX300/K30 gateway and the MyBuderus PointT API.

Current status:

- MVP for K30/MX300 gateways with sensors, conservative switches, and selected numeric setpoints.
- Uses SingleKey Authorization Code + PKCE to obtain access and refresh tokens.
- Write/control support is currently limited to PointT resources that are confirmed as writeable on the tested gateway:
  - Extra hot water (`/dhwCircuits/dhw1/charge`)
  - DHW temperature reduction on alarm (`/dhwCircuits/dhw1/reduceTempOnAlarm`)
  - Heating circuit manual room setpoint (`/heatingCircuits/hc1/manualRoomSetpoint`)
  - Extra hot water duration (`/dhwCircuits/dhw1/chargeDuration`)
  - Extra hot water target temperature (`/dhwCircuits/dhw1/singleChargeSetpoint`)

Confirmed resources from the first MX300/K30 capture:

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

## Local testing

Copy `custom_components/buderus_ha` into a Home Assistant `custom_components` directory, restart Home Assistant, then add the integration from the UI.

Initial setup currently only works reliably in a desktop browser. On iPhone or Android, the installed MyBuderus app can intercept the final `com.buderus.tt.dashtt://app/login` redirect, so Home Assistant cannot receive the authorization code.

On Windows, the friendliest setup path is to register the local redirect helper before starting the Home Assistant config flow:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\register_windows_oauth_redirect_helper.ps1
```

Then start the Buderus MX300 setup in Home Assistant, open the SingleKey login URL on the PC, and sign in. When the browser asks whether it should open an external app for `com.buderus.tt.dashtt://`, allow it. The helper copies the final redirect URL to the clipboard. Paste that URL into the Home Assistant setup form.

After setup, the helper can be removed again:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\unregister_windows_oauth_redirect_helper.ps1
```

Fallback without the helper: open the SingleKey login URL in a desktop browser. Before signing in, open the browser developer tools, go to the Network tab, and enable "Preserve log". Then sign in and paste the final redirect URL that starts with:

```text
com.buderus.tt.dashtt://app/login
```

If SingleKey shows a network or protocol error after login and the final URL is not visible in the address bar, copy the `Location` response header from the last `/auth/connect/authorize/callback` redirect in the Network tab.

The integration exchanges the authorization code with PKCE and stores the returned refresh token for automatic token renewal.

SingleKey constraints found during research:

- The MyBuderus client accepts the app redirect URI `com.buderus.tt.dashtt://app/login`.
- A normal HTTP callback URL is rejected as a misconfigured application.
- The production SingleKey server returns 404 for the tested OAuth device-code endpoint.
- On iPhone, the final app redirect is likely handled by the MyBuderus app, so desktop browser setup is currently the most reliable path.

## Research helper

`tools/probe_pointt.ps1` can query known PointT resources with a token from the clipboard:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\probe_pointt.ps1 -UseClipboard
```

The helper stores responses under `.analysis/pointt`, which is intentionally ignored by Git because it can contain device identifiers and serial numbers.

`tools/oauth_pointt_login.py` can test the SingleKey Authorization Code + PKCE flow outside Home Assistant:

```powershell
python .\tools\oauth_pointt_login.py
```

It writes token data under `.analysis/auth`, which is also ignored by Git.

`tools/oauth_callback_login.py` tests whether SingleKey accepts an HTTP callback URL. If it works, the authorization code is received automatically without copying the final redirect URL:

```powershell
python .\tools\oauth_callback_login.py
```

To test the same idea from a phone on the local network, bind to all interfaces and use the PC's LAN address:

```powershell
python .\tools\oauth_callback_login.py --host 0.0.0.0 --public-base-url http://<PC_LAN_IP>:8765 --no-open
```

Then open `http://<PC_LAN_IP>:8765/` on the phone. If SingleKey accepts that redirect URI, the helper receives the code automatically. If SingleKey rejects it, the app-style redirect remains the only known working redirect URI for this client.

`tools/oauth_device_login.py` tests whether SingleKey allows the OAuth device-code flow for the MyBuderus client. This would be the most phone-friendly setup path because Home Assistant could show a code and the user could authorize it on any browser without copying redirect URLs:

```powershell
python .\tools\oauth_device_login.py
```

The production SingleKey server currently returns 404 for the tested device-code endpoint, so the app-style redirect flow remains the only confirmed working SingleKey path.
