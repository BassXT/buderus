from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
import json
from typing import Any

import aiohttp

from .const import DEFAULT_USER_AGENT, POINTT_BASE_URL


class BuderusApiError(Exception):
    """Raised when the Buderus/Bosch PointT API returns an unexpected response."""


class BuderusAuthError(BuderusApiError):
    """Raised when the current access token is rejected."""


class BuderusPointTClient:
    """Small async client for the Bosch/Buderus PointT API used by MyBuderus."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str | Callable[[], str | Awaitable[str]],
        *,
        base_url: str = POINTT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._session = session
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent

    async def get_gateways(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/gateways/")
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        raise BuderusApiError("Unexpected gateway list response")

    async def get_gateway(self, gateway_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/gateways/{gateway_id}")
        if not isinstance(data, dict):
            raise BuderusApiError("Unexpected gateway response")
        return data

    async def get_partnumber(self, gateway_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/gateways/{gateway_id}/partnumber")
        if not isinstance(data, dict):
            raise BuderusApiError("Unexpected part number response")
        return data

    async def get_resource(self, gateway_id: str, resource_path: str) -> dict[str, Any]:
        path = resource_path.strip("/")
        data = await self._request("GET", f"/gateways/{gateway_id}/resource/{path}")
        if not isinstance(data, dict):
            raise BuderusApiError(f"Unexpected resource response for {resource_path}")
        return data

    async def set_resource_value(
        self,
        gateway_id: str,
        resource_path: str,
        value: Any,
        *,
        resource_type: str | None = None,
    ) -> None:
        path = resource_path.strip("/")
        payloads: list[dict[str, Any]] = [{"value": value}]
        if resource_type:
            payloads.append(
                {
                    "id": f"/{path}",
                    "type": resource_type,
                    "writeable": 1,
                    "value": value,
                }
            )

        last_error: BuderusApiError | None = None
        for payload in payloads:
            try:
                await self._request("PUT", f"/gateways/{gateway_id}/resource/{path}", json_body=payload)
                return
            except BuderusAuthError:
                raise
            except BuderusApiError as err:
                last_error = err

        if last_error is not None:
            raise last_error

    async def _request(self, method: str, path: str, *, json_body: Any | None = None) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        access_token = await self._get_access_token()
        headers = {
            "Accept": "application/json",
            "Accept-Charset": "UTF-8",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }

        async with self._session.request(method, url, headers=headers, json=json_body) as response:
            if response.status in (401, 403):
                raise BuderusAuthError(f"API authentication failed: {response.status}")
            if response.status >= 400:
                body = await response.text()
                raise BuderusApiError(f"API request failed: {response.status} {body}")
            if response.status == 204:
                return None
            body = await response.text()
            if not body:
                return None
            try:
                return json.loads(body)
            except Exception as err:  # noqa: BLE001 - aiohttp can raise multiple parser errors.
                raise BuderusApiError(f"Invalid JSON response from {url}: {body}") from err

    async def _get_access_token(self) -> str:
        if callable(self._access_token):
            token = self._access_token()
            if isawaitable(token):
                token = await token
        else:
            token = self._access_token
        return str(token).removeprefix("Bearer ").strip()
