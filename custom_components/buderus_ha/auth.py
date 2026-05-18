from __future__ import annotations

import base64
import hashlib
import secrets
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from .api import BuderusApiError, BuderusAuthError
from .const import (
    DEFAULT_USER_AGENT,
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPES,
    OAUTH_STYLE_ID,
    OAUTH_TOKEN_URL,
)


def create_code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()


def create_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def create_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(code_verifier: str, state: str) -> str:
    query = {
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "code_challenge": create_code_challenge(code_verifier),
        "code_challenge_method": "S256",
        "prompt": "login",
        "style_id": OAUTH_STYLE_ID,
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urlencode(query)}"


def parse_authorization_response(value: str, expected_state: str | None = None) -> str:
    value = value.strip()
    if value.startswith("http") or value.startswith(OAUTH_REDIRECT_URI):
        parsed = urlparse(value)
        params = parse_qs(parsed.query or parsed.fragment)
        if "error" in params:
            description = params.get("error_description", params["error"])[0]
            raise BuderusAuthError(description)
        if expected_state and params.get("state", [None])[0] != expected_state:
            raise BuderusAuthError("OAuth state did not match")
        code = params.get("code", [None])[0]
        if not code:
            raise BuderusAuthError("No authorization code found in redirect URL")
        return code
    return value


class BuderusOAuthClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        return await self._token_request(
            {
                "grant_type": "authorization_code",
                "client_id": OAUTH_CLIENT_ID,
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": OAUTH_REDIRECT_URI,
            }
        )

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        return await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": OAUTH_CLIENT_ID,
                "refresh_token": refresh_token,
            }
        )

    async def _token_request(self, data: dict[str, str]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        async with self._session.post(OAUTH_TOKEN_URL, data=data, headers=headers) as response:
            body = await response.text()
            if response.status in (400, 401, 403):
                raise BuderusAuthError(f"Token request failed: {response.status} {body}")
            if response.status >= 400:
                raise BuderusApiError(f"Token request failed: {response.status} {body}")
            token_data = await response.json(content_type=None)

        if "access_token" not in token_data:
            raise BuderusAuthError("Token response did not include an access token")
        if "expires_in" in token_data:
            token_data["expires_at"] = int(time.time()) + int(token_data["expires_in"])
        return token_data
