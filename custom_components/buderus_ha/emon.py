"""Helpers for validated energy-monitoring values."""

from __future__ import annotations

from math import fsum, isfinite
from typing import Any


def extract_emon_values(payload: dict[str, Any]) -> dict[str, float]:
    """Return finite, non-negative numeric values from an EMON payload."""
    raw_values = payload.get("values")
    if not isinstance(raw_values, list):
        return {}

    values: dict[str, float] = {}
    for item in raw_values:
        if not isinstance(item, dict):
            continue
        for key, raw_value in item.items():
            if not isinstance(key, str) or isinstance(raw_value, bool):
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if isfinite(value) and value >= 0:
                values[key] = value

    return values


def emon_value(payload: dict[str, Any], key: str) -> float | None:
    """Return one validated EMON value."""
    return extract_emon_values(payload).get(key)


def total_electricity(payload: dict[str, Any]) -> float | None:
    """Return the API total or a complete compressor/heater sum.

    Missing components are never interpreted as zero. This avoids reporting a
    plausible but incomplete total when the API returns only a partial payload.
    """
    values = extract_emon_values(payload)
    if "electricity" in values:
        return values["electricity"]

    compressor = values.get("compressor")
    electric_heater = values.get("eheater")
    if compressor is None or electric_heater is None:
        return None
    return fsum((compressor, electric_heater))
