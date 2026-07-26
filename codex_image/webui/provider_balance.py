from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import httpx

_QUOTA_PER_USD = 500_000
_BALANCE_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class ProviderBalanceResult:
    status: str
    remaining_usd: float | None = None
    used_usd: float | None = None
    total_usd: float | None = None
    remaining: float | None = None
    unit: str | None = None

    def public_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": self.status}
        if self.status == "ok":
            if any(value is not None for value in (self.remaining_usd, self.used_usd, self.total_usd)):
                payload.update(
                    {
                        "remaining_usd": self.remaining_usd,
                        "used_usd": self.used_usd,
                        "total_usd": self.total_usd,
                    }
                )
            if self.remaining is not None and self.unit:
                payload.update({"remaining": self.remaining, "unit": self.unit})
        return payload


def _quota_value(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("invalid_balance_payload")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError("invalid_balance_payload")
    return parsed


def parse_new_api_balance(payload: Mapping[str, Any]) -> ProviderBalanceResult:
    data = payload.get("data")
    if not isinstance(data, Mapping) or "quota" not in data or "used_quota" not in data:
        raise ValueError("invalid_balance_payload")
    quota = _quota_value(data["quota"])
    used_quota = _quota_value(data["used_quota"])
    return ProviderBalanceResult(
        status="ok",
        remaining_usd=quota / _QUOTA_PER_USD,
        used_usd=used_quota / _QUOTA_PER_USD,
        total_usd=(quota + used_quota) / _QUOTA_PER_USD,
    )


def parse_sub2api_balance(payload: Mapping[str, Any]) -> ProviderBalanceResult:
    if payload.get("isValid") is False or payload.get("is_active") is False:
        raise ValueError("invalid_balance_payload")
    unit = str(payload.get("unit") or "USD").strip().upper()
    if unit not in {"USD", "$"}:
        raise ValueError("invalid_balance_payload")
    remaining = payload.get("remaining")
    if remaining is None:
        remaining = payload.get("balance")
    return ProviderBalanceResult(
        status="ok",
        remaining_usd=_quota_value(remaining),
    )


def parse_wisart_balance(payload: Mapping[str, Any]) -> ProviderBalanceResult:
    user = payload.get("user")
    if not isinstance(user, Mapping) or "points" not in user:
        raise ValueError("invalid_balance_payload")
    return ProviderBalanceResult(
        status="ok",
        remaining=_quota_value(user["points"]),
        unit="POINTS",
    )


def _wisart_profile_url(balance_url: str) -> str:
    parsed = urlsplit(balance_url)
    path = parsed.path.rstrip("/")
    if path.lower().endswith("/v1"):
        path = path[:-3].rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/api/auth/me", "", ""))


def _sub2api_usage_url(balance_url: str) -> str:
    lowered = balance_url.lower()
    if lowered.endswith("/usage"):
        return balance_url
    if lowered.endswith("/v1"):
        return f"{balance_url}/usage"
    return f"{balance_url}/v1/usage"


def fetch_provider_balance(
    provider: Mapping[str, Any],
    *,
    client: httpx.Client | None = None,
) -> ProviderBalanceResult:
    protocol = str(provider.get("balance_protocol") or "new_api").strip().lower()
    balance_url = str(provider.get("balance_url") or "").strip().rstrip("/")
    balance_token = str(provider.get("balance_token") or "").strip()
    if protocol == "wisart":
        balance_url = balance_url or str(provider.get("base_url") or "").strip().rstrip("/")
        balance_token = balance_token or str(provider.get("api_key") or "").strip()
    if not balance_url or not balance_token:
        return ProviderBalanceResult(status="unavailable")

    headers = {
        "Authorization": f"Bearer {balance_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "cc-switch/1.0",
    }
    if protocol == "sub2api":
        request_url = _sub2api_usage_url(balance_url)
    elif protocol == "wisart":
        request_url = _wisart_profile_url(balance_url)
    else:
        request_url = f"{balance_url}/api/user/self"
        balance_user_id = str(provider.get("balance_user_id") or "").strip()
        if balance_user_id:
            headers["New-Api-User"] = balance_user_id

    owns_client = client is None
    request_client = client or httpx.Client()
    try:
        response = request_client.get(
            request_url,
            headers=headers,
            timeout=_BALANCE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise ValueError("invalid_balance_payload")
        if protocol == "sub2api":
            return parse_sub2api_balance(payload)
        if protocol == "wisart":
            return parse_wisart_balance(payload)
        return parse_new_api_balance(payload)
    except (httpx.HTTPError, ValueError, TypeError):
        return ProviderBalanceResult(status="unavailable")
    finally:
        if owns_client:
            request_client.close()


__all__ = (
    "ProviderBalanceResult",
    "fetch_provider_balance",
    "parse_new_api_balance",
    "parse_sub2api_balance",
    "parse_wisart_balance",
)
