"""Tests for energy-monitoring value validation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "buderus_ha" / "emon.py"
SPEC = importlib.util.spec_from_file_location("buderus_emon", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
EMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EMON)


class EmonValuesTest(unittest.TestCase):
    """Verify extraction and total calculations without API assumptions."""

    def test_verified_total_payload(self) -> None:
        fixture_path = ROOT / "tests" / "fixtures" / "emon_total.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        self.assertEqual(EMON.emon_value(payload, "compressor"), 33.18)
        self.assertEqual(EMON.emon_value(payload, "eheater"), 0)
        self.assertEqual(EMON.emon_value(payload, "outputProduced"), 75.04)
        self.assertAlmostEqual(EMON.total_electricity(payload), 33.18)
        self.assertAlmostEqual(EMON.environmental_energy(payload), 41.86)

    def test_api_total_takes_precedence(self) -> None:
        payload = {
            "values": [
                {"electricity": 41.25},
                {"compressor": 30},
                {"eheater": 5},
            ]
        }

        self.assertEqual(EMON.total_electricity(payload), 41.25)

    def test_derived_total_requires_both_components(self) -> None:
        self.assertIsNone(
            EMON.total_electricity({"values": [{"compressor": 27.35}]})
        )
        self.assertIsNone(
            EMON.total_electricity({"values": [{"eheater": 3.85}]})
        )

    def test_zero_is_a_valid_counter_value(self) -> None:
        payload = {"values": [{"compressor": 0}, {"eheater": 0}]}

        self.assertEqual(EMON.total_electricity(payload), 0)

    def test_environmental_energy_requires_complete_balance(self) -> None:
        self.assertIsNone(
            EMON.environmental_energy(
                {"values": [{"outputProduced": 75.04}, {"compressor": 33.18}]}
            )
        )

    def test_negative_environmental_energy_is_rejected(self) -> None:
        payload = {
            "values": [
                {"outputProduced": 10},
                {"compressor": 12},
                {"eheater": 0},
            ]
        }

        self.assertIsNone(EMON.environmental_energy(payload))

    def test_invalid_values_are_ignored(self) -> None:
        payload = {
            "values": [
                {"negative": -1},
                {"boolean": True},
                {"nan": "NaN"},
                {"infinite": "Infinity"},
                {"text": "not-a-number"},
                {"numeric_string": "12.5"},
                None,
            ]
        }

        self.assertEqual(
            EMON.extract_emon_values(payload),
            {"numeric_string": 12.5},
        )

    def test_malformed_payload_is_empty(self) -> None:
        self.assertEqual(EMON.extract_emon_values({}), {})
        self.assertEqual(EMON.extract_emon_values({"values": {}}), {})


if __name__ == "__main__":
    unittest.main()
