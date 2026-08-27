"""Helpers for Home Assistant enum sensor states."""

from __future__ import annotations

import re
from collections.abc import Collection


def enum_slug(value: str) -> str:
    """Convert a Bosch/PointT value to a translation-safe state."""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)
    return value.strip("_").lower() or "unknown"


def enum_state(value: str, options: Collection[str] | None) -> str | None:
    """Return a normalized state only when it is declared by the entity."""
    state = enum_slug(value)
    return state if options is None or state in options else None
