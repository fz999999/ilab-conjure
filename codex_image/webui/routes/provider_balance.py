from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from codex_image.webui.context import WebUIContext
from codex_image.webui.provider_balance import fetch_provider_balance


def register_provider_balance_routes(app: FastAPI, ctx: WebUIContext) -> None:
    @app.get("/api/provider-balances/{provider_id}")
    def provider_balance(provider_id: str) -> dict[str, Any]:
        settings = ctx.api_settings.read()
        provider = next(
            (item for item in settings.get("providers") or [] if item.get("id") == provider_id),
            None,
        )
        if provider is None:
            return {"provider_id": provider_id, "status": "unavailable"}
        result = fetch_provider_balance(provider)
        return {"provider_id": provider_id, **result.public_payload()}


__all__ = ("register_provider_balance_routes",)
