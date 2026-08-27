"""Tests for enum value normalization and validation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "buderus_ha" / "enum_helpers.py"
SPEC = importlib.util.spec_from_file_location("buderus_enum_helpers", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ENUM_HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENUM_HELPERS)


class EnumHelpersTest(unittest.TestCase):
    """Verify enum normalization and undeclared-value handling."""

    def test_normalizes_pointt_values(self) -> None:
        self.assertEqual(ENUM_HELPERS.enum_slug("manualOnHigh"), "manual_on_high")
        self.assertEqual(ENUM_HELPERS.enum_slug(" CH + DHW "), "ch_dhw")

    def test_declared_value_is_preserved(self) -> None:
        self.assertEqual(
            ENUM_HELPERS.enum_state("cooling", ["off", "cooling"]),
            "cooling",
        )

    def test_undeclared_value_becomes_unknown(self) -> None:
        self.assertIsNone(
            ENUM_HELPERS.enum_state("futureValue", ["off", "cooling"])
        )

    def test_unrestricted_enum_accepts_normalized_value(self) -> None:
        self.assertEqual(ENUM_HELPERS.enum_state("heatCool", None), "heat_cool")


if __name__ == "__main__":
    unittest.main()
