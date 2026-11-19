"""Tests for OAuth redirect parsing."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "buderus_ha"
sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
PACKAGE = types.ModuleType("buderus_ha")
PACKAGE.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault("buderus_ha", PACKAGE)
AUTH = importlib.import_module("buderus_ha.auth")


class AuthorizationResponseTest(unittest.TestCase):
    """Verify redirect URL errors surface as auth errors."""

    def test_state_mismatch_raises_auth_error(self) -> None:
        with self.assertRaisesRegex(AUTH.BuderusAuthError, "OAuth state did not match"):
            AUTH.parse_authorization_response(
                "https://example.com/callback?code=abc&state=other",
                "expected",
            )


if __name__ == "__main__":
    unittest.main()
