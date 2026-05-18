from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

AUTHORIZE_URL = "https://singlekey-id.com/auth/connect/authorize"
SINGLEKEY_BASE_URL = "https://singlekey-id.com"
TOKEN_URL = "https://singlekey-id.com/auth/connect/token"
CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
REDIRECT_URI = "com.buderus.tt.dashtt://app/login"
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


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def token_request(payload: dict[str, str]) -> dict:
    body = urlencode(payload).encode()
    request = Request(
        TOKEN_URL,
        data=body,
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
        raise SystemExit(f"Token request failed: HTTP {err.code} {detail}") from err


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


def extract_authorization_code(value: str, expected_state: str) -> str | None:
    if not value.startswith("http") and not value.startswith(REDIRECT_URI):
        return value

    parsed = urlparse(value)
    params = parse_qs(parsed.query or parsed.fragment)

    if not params.get("code") and params.get("returnUrl"):
        next_url = urljoin(SINGLEKEY_BASE_URL, params["returnUrl"][0])
        print("\nThis is a SingleKey intermediate redirect, not the final app redirect.")
        print("Open this URL in the same browser session, then paste the next URL/code:")
        print(next_url)
        return None

    if params.get("state", [None])[0] != expected_state:
        raise SystemExit("OAuth state mismatch")

    return params.get("code", [None])[0]


def main() -> None:
    code_verifier = b64url(secrets.token_bytes(64))
    code_challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())
    state = secrets.token_urlsafe(32)

    authorization_url = f"{AUTHORIZE_URL}?{urlencode({
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'prompt': 'login',
        'style_id': 'tt_bud',
    })}"

    print("Open this URL in your browser and sign in:\n")
    print(authorization_url)
    print("\nPaste the final redirect URL or just the code below.")

    code = None
    while not code:
        redirect = input("> ").strip()
        code = extract_authorization_code(redirect, state)

    if not code:
        raise SystemExit("No authorization code found")

    token_data = token_request(
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": REDIRECT_URI,
        }
    )
    token_data["expires_at"] = int(time.time()) + int(token_data.get("expires_in", 0))

    gateway_data = pointt_get("/gateways/", token_data["access_token"])

    out_dir = Path(".analysis/auth")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens.json").write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    (out_dir / "gateways.json").write_text(json.dumps(gateway_data, indent=2), encoding="utf-8")

    print("\nOAuth login worked.")
    print(f"Saved token data to {out_dir / 'tokens.json'}")
    print(f"Gateway response: {json.dumps(gateway_data, indent=2)}")


if __name__ == "__main__":
    main()
