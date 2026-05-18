from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

AUTHORIZE_URL = "https://singlekey-id.com/auth/connect/authorize"
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


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def token_request(payload: dict[str, str]) -> dict:
    request = Request(
        TOKEN_URL,
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


def make_handler(
    authorization_url: str,
    expected_state: str,
    result: dict[str, str],
    done: threading.Event,
) -> type[BaseHTTPRequestHandler]:
    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(
                    200,
                    "<h1>Buderus MX300 OAuth test</h1>"
                    "<p>Open the SingleKey login from here. If this redirect URI is accepted, "
                    "this helper receives the code automatically.</p>"
                    f"<p><a href=\"{html.escape(authorization_url)}\">Start SingleKey login</a></p>",
                )
                return

            if parsed.path != "/callback":
                self._send_html(404, "<h1>Not found</h1>")
                return

            params = parse_qs(parsed.query)
            state = params.get("state", [None])[0]
            if state != expected_state:
                result["error"] = "OAuth state mismatch"
                self._send_html(400, "<h1>OAuth state mismatch</h1>")
                done.set()
                return

            if params.get("error"):
                description = params.get("error_description", params["error"])[0]
                result["error"] = description
                self._send_html(400, f"<h1>OAuth error</h1><p>{html.escape(description)}</p>")
                done.set()
                return

            code = params.get("code", [None])[0]
            if not code:
                result["error"] = "No authorization code in callback"
                self._send_html(400, "<h1>No authorization code in callback</h1>")
                done.set()
                return

            result["code"] = code
            self._send_html(
                200,
                "<h1>OAuth code received</h1>"
                "<p>You can close this browser tab and return to the terminal.</p>",
            )
            done.set()

        def _send_html(self, status: int, body: str) -> None:
            payload = (
                "<!doctype html><html><head><meta charset=\"utf-8\">"
                "<title>Buderus MX300 OAuth test</title></head><body>"
                f"{body}</body></html>"
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return OAuthCallbackHandler


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test whether SingleKey accepts an HTTP callback redirect URI."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the local callback server to.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local callback server.")
    parser.add_argument(
        "--public-base-url",
        help="Base URL used as redirect URI host, for example http://<PC_LAN_IP>:8765.",
    )
    parser.add_argument("--no-open", action="store_true", help="Only print the URL, do not open a browser.")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds to wait for the OAuth callback.")
    args = parser.parse_args()

    public_base_url = (args.public_base_url or f"http://127.0.0.1:{args.port}").rstrip("/")
    redirect_uri = f"{public_base_url}/callback"

    code_verifier = b64url(secrets.token_bytes(64))
    code_challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())
    state = secrets.token_urlsafe(32)
    authorization_url = f"{AUTHORIZE_URL}?{urlencode({
        'client_id': CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'prompt': 'login',
        'style_id': 'tt_bud',
    })}"

    result: dict[str, str] = {}
    done = threading.Event()
    handler = make_handler(authorization_url, state, result, done)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    landing_url = f"{public_base_url}/"
    print(f"Listening on http://{args.host}:{args.port}")
    print(f"Testing redirect URI: {redirect_uri}")
    print(f"Open this local helper page: {landing_url}")

    if not args.no_open:
        webbrowser.open(landing_url)

    try:
        if not done.wait(args.timeout):
            raise SystemExit(
                "Timed out waiting for OAuth callback. "
                "If the browser showed an invalid redirect_uri error, SingleKey does not accept this callback URL."
            )

        if result.get("error"):
            raise SystemExit(result["error"])

        token_data = token_request(
            {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": result["code"],
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            }
        )
        token_data["expires_at"] = int(time.time()) + int(token_data.get("expires_in", 0))
        gateway_data = pointt_get("/gateways/", token_data["access_token"])

        out_dir = Path(".analysis/auth_callback")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tokens.json").write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        (out_dir / "gateways.json").write_text(json.dumps(gateway_data, indent=2), encoding="utf-8")

        print("\nOAuth callback login worked.")
        print(f"Saved token data to {out_dir / 'tokens.json'}")
        print(f"Gateway response: {json.dumps(gateway_data, indent=2)}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
