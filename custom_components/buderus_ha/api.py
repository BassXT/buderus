"""Async client for the Bosch/Buderus PointT API used by MyBuderus."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
import json
import logging
import re
from typing import Any

import aiohttp

from .const import (
    DEFAULT_USER_AGENT,
    EMON_LIFETIME_PATHS,
    EMON_RECORDING_BASE,
    POINTT_BASE_URL,
)

LOGGER = logging.getLogger(__name__)


class BuderusApiError(Exception):
    """Raised when the Buderus/Bosch PointT API returns an unexpected response."""


class BuderusAuthError(BuderusApiError):
    """Raised when the API rejects the request with 401/403.

    Achtung: Die pointt-API liefert auch dann 403, wenn eine Ressource am
    Gateway schlicht nicht existiert (z. B. ein zweiter Wärmeerzeuger).
    Deshalb traegt die Exception den HTTP-Status mit: 401 bedeutet
    "Token abgelaufen/ungueltig" und muss nach oben durchgereicht werden,
    403 darf beim Abtasten optionaler Ressourcen uebersprungen werden.
    """

    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.status = status


def _snake(name: str) -> str:
    """outputProduced -> output_produced"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def _flatten_emon_values(payload: dict[str, Any]) -> dict[str, float]:
    """values:[{"compressor":27.35},{"eheater":3.85}] -> flaches Dict."""
    out: dict[str, float] = {}
    for entry in payload.get("values") or []:
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            try:
                out[_snake(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return out


class BuderusPointTClient:
    """Small async client for the Bosch/Buderus PointT API used by MyBuderus."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str | Callable[[], str | Awaitable[str]],
        *,
        base_url: str = POINTT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        token_refresh: Callable[[], Any] | None = None,
    ) -> None:
        self._session = session
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._token_refresh = token_refresh

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

    async def get_resource(
        self,
        gateway_id: str,
        resource_path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        path = resource_path.strip("/")
        data = await self._request(
            "GET", f"/gateways/{gateway_id}/resource/{path}", params=params
        )
        if not isinstance(data, dict):
            raise BuderusApiError(f"Unexpected resource response for {resource_path}")
        return data

    # --- Energy Monitoring ---------------------------------------------

    async def get_emon(self, gateway_id: str) -> dict[str, float]:
        """Liest alle vorhandenen EMON-Lifetime-Zaehler in kWh.

        Nicht vorhandene Domains (403) werden uebersprungen, nicht als Fehler
        gewertet. Ein abgelaufener Token (401) wird dagegen durchgereicht,
        damit der Coordinator den Reauth-Flow anstossen kann.
        Ergebnis-Keys: '<domain>_<feld>', z. B. 'dhw_compressor'.
        """
        result: dict[str, float] = {}

        for domain, path in EMON_LIFETIME_PATHS.items():
            try:
                payload = await self.get_resource(gateway_id, path)
            except BuderusAuthError as err:
                if err.status == 401:
                    # Token tot - nicht als "Domain fehlt" missdeuten.
                    raise
                LOGGER.debug("EMON-Domain %s nicht vorhanden (403)", domain)
                continue
            except BuderusApiError as err:
                LOGGER.debug("EMON-Domain %s fehlgeschlagen: %s", domain, err)
                continue
            for field, value in _flatten_emon_values(payload).items():
                result[f"{domain}_{field}"] = value

        for domain in EMON_LIFETIME_PATHS:
            compressor = result.get(f"{domain}_compressor")
            eheater = result.get(f"{domain}_eheater")
            if compressor is None and eheater is None:
                continue
            result[f"{domain}_electric"] = round(
                (compressor or 0.0) + (eheater or 0.0), 2
            )

        electric = result.get("total_electric")
        produced = result.get("total_output_produced")
        if electric and produced is not None:
            result["scop"] = round(produced / electric, 2)

        if not result:
            # Lieber ein lauter Fehler als zehn Sensoren, die still verschwinden.
            raise BuderusApiError("Keine EMON-Daten erhalten")

        return result

    async def get_emon_recording(
        self,
        gateway_id: str,
        domain: str,
        sub: str,
        interval: str,
    ) -> dict[str, Any]:
        """Zeitreihe holen. interval: 'YYYY-MM-DD' | 'YYYY-MM' | 'YYYY'."""
        return await self.get_resource(
            gateway_id,
            f"{EMON_RECORDING_BASE}/{domain}/{sub}",
            params={"interval": interval},
        )

    @staticmethod
    def sum_recording(payload: dict[str, Any]) -> float:
        """Summiert die y-Werte einer yRecording-Antwort."""
        total = 0.0
        for point in payload.get("recording") or []:
            if not isinstance(point, dict):
                continue
            try:
                total += float(point.get("y") or 0.0)
            except (TypeError, ValueError):
                continue
        return round(total, 2)

    # --- Schreiben -------------------------------------------------------

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
                await self._request(
                    "PUT", f"/gateways/{gateway_id}/resource/{path}", json_body=payload
                )
                return
            except BuderusAuthError:
                raise
            except BuderusApiError as err:
                last_error = err

        if last_error is not None:
            raise last_error

    # --- Transport -------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: Any | None = None,
        retry_auth: bool = True,
    ) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        access_token = await self._get_access_token()
        headers = {
            "Accept": "application/json",
            "Accept-Charset": "UTF-8",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }

        async with self._session.request(
            method, url, headers=headers, params=params, json=json_body
        ) as response:
            status = response.status

            if status in (401, 403):
                body = await response.text()
                LOGGER.debug(
                    "PointT %s %s -> %s | body=%r", method, url, status, body
                )
                if status == 401 and retry_auth and self._token_refresh is not None:
                    LOGGER.debug("401 erhalten - Token erneuern und einmal wiederholen")
                    refreshed = self._token_refresh()
                    if isawaitable(refreshed):
                        await refreshed
                    return await self._request(
                        method,
                        path,
                        params=params,
                        json_body=json_body,
                        retry_auth=False,
                    )
                raise BuderusAuthError(
                    f"API request rejected: {status} {body}", status
                )

            if status >= 400:
                body = await response.text()
                raise BuderusApiError(f"API request failed: {status} {body}")

            if status == 204:
                return None

            body = await response.text()
            if not body:
                return None
            try:
                return json.loads(body)
            except Exception as err:  # noqa: BLE001
                raise BuderusApiError(
                    f"Invalid JSON response from {url}: {body}"
                ) from err

    async def _get_access_token(self) -> str:
        if callable(self._access_token):
            token = self._access_token()
            if isawaitable(token):
                token = await token
        else:
            token = self._access_token
        return str(token).removeprefix("Bearer ").strip()
