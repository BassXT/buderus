from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DISCOVERY_URLS = (
    "https://singlekey-id.com/auth/.well-known/openid-configuration",
    "https://singlekey-id.com/.well-known/openid-configuration",
)
DEVICE_AUTHORIZATION_FALLBACK_URL = "https://singlekey-id.com/auth/connect/deviceauthorization"
TOKEN_URL = "https://singlekey-id.com/auth/connect/token"
CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
USER_AGENT = "DashApp/3.7.0 (iOS-Release)"
POINTT_BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1"
SCOPES = (
    "openid",
    "email",
    "profile",
    "offline_access",
    "pointt.gateway.claiming",
    "pointt.gateway.removal",
    "pointt.gateway.list",
    "pointt.gateway.users",
    "pointt.gateway.resource.dashapp",
    "pointt.castt.flow.token-exchange",
    "bacon",
    "hcc.tariff.read",
)
DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def post_form(url: str, payload: dict[str, str]) -> dict:
    request = Request(
        url,
        data=urlencode(payload).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as err:
        detail = err.read().decode(errors="replace")
        content_type = err.headers.get("Content-Type", "")
        if "text/html" in content_type:
            raise SystemExit(
                f"HTTP {err.code}: {url} returned an HTML error page. "
                "SingleKey does not expose this OAuth device-code endpoint."
            ) from err
        try:
            data = json.loads(detail)
        except json.JSONDecodeError:
            raise SystemExit(f"HTTP {err.code}: {detail}") from err
        data["_http_status"] = err.code
        return data


def discover_device_endpoint() -> tuple[str, str]:
    last_error = None
    for discovery_url in DISCOVERY_URLS:
        try:
            metadata = fetch_json(discovery_url)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as err:
            last_error = err
            continue

        device_endpoint = metadata.get("device_authorization_endpoint")
        token_endpoint = metadata.get("token_endpoint") or TOKEN_URL
        if device_endpoint:
            return device_endpoint, token_endpoint

    if last_error:
        print(f"SingleKey discovery metadata was not available: {last_error}")
    else:
        print("SingleKey discovery metadata does not advertise a device authorization endpoint.")
    print(f"Trying fallback endpoint: {DEVICE_AUTHORIZATION_FALLBACK_URL}")
    return DEVICE_AUTHORIZATION_FALLBACK_URL, TOKEN_URL


def pointt_get(path: str, access_token: str) -> dict:
    request = Request(
        f"{POINTT_BASE_URL}/{path.lstrip('/')}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as err:
        detail = err.read().decode(errors="replace")
        raise SystemExit(f"PointT request failed: HTTP {err.code} {detail}") from err


def main() -> None:
    device_endpoint, token_endpoint = discover_device_endpoint()
    print(f"Device authorization endpoint: {device_endpoint}")

    device_data = post_form(
        device_endpoint,
        {
            "client_id": CLIENT_ID,
            "scope": " ".join(SCOPES),
        },
    )
    if device_data.get("error"):
        description = device_data.get("error_description") or device_data["error"]
        raise SystemExit(f"Device authorization failed: {description}")

    verification_uri = device_data.get("verification_uri_complete") or device_data.get("verification_uri")
    user_code = device_data.get("user_code")
    device_code = device_data.get("device_code")
    if not verification_uri or not user_code or not device_code:
        raise SystemExit(f"Unexpected device authorization response: {json.dumps(device_data, indent=2)}")

    print("\nOpen this SingleKey URL on any device:")
    print(verification_uri)
    print(f"\nEnter this user code if the page asks for it: {user_code}")
    print("\nWaiting for authorization...")

    interval = int(device_data.get("interval", 5))
    expires_at = time.time() + int(device_data.get("expires_in", 600))
    token_data = None

    while time.time() < expires_at:
        time.sleep(interval)
        poll_data = post_form(
            token_endpoint,
            {
                "grant_type": DEVICE_GRANT_TYPE,
                "client_id": CLIENT_ID,
                "device_code": device_code,
            },
        )

        error = poll_data.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error:
            description = poll_data.get("error_description") or error
            raise SystemExit(f"Token polling failed: {description}")

        token_data = poll_data
        break

    if not token_data:
        raise SystemExit("Timed out waiting for device authorization")

    token_data["expires_at"] = int(time.time()) + int(token_data.get("expires_in", 0))
    gateway_data = pointt_get("/gateways/", token_data["access_token"])

    out_dir = Path(".analysis/auth_device")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens.json").write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    (out_dir / "gateways.json").write_text(json.dumps(gateway_data, indent=2), encoding="utf-8")

    print("\nOAuth device login worked.")
    print(f"Saved token data to {out_dir / 'tokens.json'}")
    print(f"Gateway response: {json.dumps(gateway_data, indent=2)}")


if __name__ == "__main__":
    main()
