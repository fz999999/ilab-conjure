from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from codex_image.webui.provider_balance import (
    fetch_provider_balance,
    parse_new_api_balance,
    parse_sub2api_balance,
    parse_wisart_balance,
)
from codex_image.webui.provider_settings import ProviderSettings
from codex_image.webui.routes.provider_balance import register_provider_balance_routes


class ProviderBalanceServiceTests(unittest.TestCase):
    def test_parses_new_api_quota_values_as_usd(self) -> None:
        result = parse_new_api_balance({"data": {"quota": 6_170_000, "used_quota": 830_000}})

        self.assertEqual(result.status, "ok")
        self.assertAlmostEqual(result.remaining_usd or 0, 12.34)
        self.assertAlmostEqual(result.used_usd or 0, 1.66)
        self.assertAlmostEqual(result.total_usd or 0, 14.0)

    def test_rejects_invalid_quota_values(self) -> None:
        invalid_values = [True, "not-a-number", -1, math.nan, math.inf]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid_balance_payload"):
                    parse_new_api_balance({"data": {"quota": value, "used_quota": 0}})

        for payload in ({}, {"data": {}}, {"data": {"quota": 1}}):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "invalid_balance_payload"):
                    parse_new_api_balance(payload)

    def test_fetch_uses_new_api_headers_and_optional_user_id(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            return httpx.Response(
                200,
                json={"data": {"quota": 500_000, "used_quota": 250_000}},
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = fetch_provider_balance(
                {
                    "balance_url": "https://relay.example",
                    "balance_token": "server-only-token",
                    "balance_user_id": "42",
                },
                client=client,
            )

        self.assertEqual(result.status, "ok")
        self.assertEqual(captured["url"], "https://relay.example/api/user/self")
        headers = captured["headers"]
        assert isinstance(headers, dict)
        self.assertEqual(headers["authorization"], "Bearer server-only-token")
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["user-agent"], "cc-switch/1.0")
        self.assertEqual(headers["new-api-user"], "42")

    def test_parses_sub2api_usage_balance_as_usd(self) -> None:
        result = parse_sub2api_balance(
            {
                "isValid": True,
                "remaining": 12.34,
                "balance": 20.0,
                "unit": "USD",
            }
        )

        self.assertEqual(result.status, "ok")
        self.assertAlmostEqual(result.remaining_usd or 0, 12.34)
        self.assertIsNone(result.used_usd)
        self.assertIsNone(result.total_usd)

    def test_sub2api_balance_falls_back_to_balance_and_rejects_invalid_payloads(self) -> None:
        fallback = parse_sub2api_balance({"remaining": None, "balance": 8.5, "unit": "USD"})
        self.assertAlmostEqual(fallback.remaining_usd or 0, 8.5)

        invalid_payloads = (
            {"isValid": False, "remaining": 1, "unit": "USD"},
            {"remaining": -1, "unit": "USD"},
            {"remaining": "1", "unit": "USD"},
            {"remaining": 1, "unit": "CNY"},
            {"unit": "USD"},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "invalid_balance_payload"):
                    parse_sub2api_balance(payload)

    def test_fetch_uses_sub2api_usage_endpoint_and_api_key(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            return httpx.Response(
                200,
                json={"isValid": True, "remaining": 9.75, "unit": "USD"},
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = fetch_provider_balance(
                {
                    "balance_protocol": "sub2api",
                    "balance_url": "https://imgapi.example/v1",
                    "balance_token": "image-api-key",
                },
                client=client,
            )

        self.assertEqual(result.status, "ok")
        self.assertAlmostEqual(result.remaining_usd or 0, 9.75)
        self.assertEqual(captured["url"], "https://imgapi.example/v1/usage")
        headers = captured["headers"]
        assert isinstance(headers, dict)
        self.assertEqual(headers["authorization"], "Bearer image-api-key")
        self.assertEqual(headers["accept"], "application/json")
        self.assertEqual(headers["user-agent"], "cc-switch/1.0")
        self.assertNotIn("new-api-user", headers)

    def test_parses_wisart_points_balance(self) -> None:
        result = parse_wisart_balance({"user": {"points": 4020}})

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.remaining, 4020)
        self.assertEqual(result.unit, "POINTS")
        self.assertIsNone(result.remaining_usd)

        for payload in ({}, {"user": {}}, {"user": {"points": -1}}, {"user": {"points": "4020"}}):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "invalid_balance_payload"):
                    parse_wisart_balance(payload)

    def test_fetch_uses_wisart_profile_endpoint_and_provider_api_key(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            return httpx.Response(200, json={"user": {"points": 4020}})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = fetch_provider_balance(
                {
                    "balance_protocol": "wisart",
                    "base_url": "https://wisart.example/v1",
                    "api_key": "wisart-api-key",
                },
                client=client,
            )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.remaining, 4020)
        self.assertEqual(result.unit, "POINTS")
        self.assertEqual(captured["url"], "https://wisart.example/api/auth/me")
        headers = captured["headers"]
        assert isinstance(headers, dict)
        self.assertEqual(headers["authorization"], "Bearer wisart-api-key")
        self.assertEqual(headers["accept"], "application/json")
        self.assertEqual(headers["user-agent"], "cc-switch/1.0")

    def test_fetch_returns_unavailable_without_config_or_on_remote_failure(self) -> None:
        self.assertEqual(fetch_provider_balance({}).status, "unavailable")

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="upstream unavailable")

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = fetch_provider_balance(
                {
                    "balance_url": "https://relay.example",
                    "balance_token": "server-only-token",
                },
                client=client,
            )
        self.assertEqual(result.status, "unavailable")


class ProviderBalanceRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "providers.json"
        self.settings = ProviderSettings(self.path)
        provider = ProviderSettings.default_provider()
        provider.update(
            {
                "id": "relay",
                "name": "Relay",
                "base_url": "https://relay.example/v1",
                "api_key": "image-api-key",
                "balance_url": "https://relay.example",
                "balance_token": "server-only-token",
                "balance_user_id": "42",
            }
        )
        for binding in provider["bindings"]:
            binding["id"] = binding["id"].replace("default", "relay")
        self.settings.write(
            {
                "schema_version": 2,
                "codex_mode": "images",
                "active_provider_id": "relay",
                "default_provider_by_model": {"gpt-image-2": "relay"},
                "providers": [provider],
            }
        )

    def test_route_never_exposes_balance_credentials(self) -> None:
        app = FastAPI()
        ctx = SimpleNamespace(api_settings=self.settings)
        register_provider_balance_routes(app, ctx)  # type: ignore[arg-type]

        from codex_image.webui.routes import provider_balance as route_module

        original = route_module.fetch_provider_balance
        route_module.fetch_provider_balance = lambda _provider: parse_new_api_balance(
            {"data": {"quota": 1_000_000, "used_quota": 500_000}}
        )
        self.addCleanup(setattr, route_module, "fetch_provider_balance", original)

        response = TestClient(app).get("/api/provider-balances/relay")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "provider_id": "relay",
                "status": "ok",
                "remaining_usd": 2.0,
                "used_usd": 1.0,
                "total_usd": 3.0,
            },
        )
        serialized = json.dumps(response.json())
        self.assertNotIn("server-only-token", serialized)
        self.assertNotIn("balance_url", serialized)

    def test_route_returns_unavailable_for_unknown_provider(self) -> None:
        app = FastAPI()
        ctx = SimpleNamespace(api_settings=self.settings)
        register_provider_balance_routes(app, ctx)  # type: ignore[arg-type]

        response = TestClient(app).get("/api/provider-balances/missing")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"provider_id": "missing", "status": "unavailable"})


if __name__ == "__main__":
    unittest.main()
