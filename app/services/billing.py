from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings


class BillingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckoutSession:
    id: str
    url: str
    customer_id: str
    subscription_id: str | None


class StripeBillingProvider:
    """Small Stripe adapter; application services do not depend on Stripe SDK types."""

    base_url = "https://api.stripe.com/v1"

    def __init__(self) -> None:
        settings = get_settings()
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        self.success_url = settings.STRIPE_SUCCESS_URL
        self.cancel_url = settings.STRIPE_CANCEL_URL
        self.timeout = settings.UPSTREAM_TIMEOUT_SECONDS

    def _headers(self) -> dict[str, str]:
        if not self.secret_key:
            raise BillingProviderError("Stripe is not configured.")
        return {"Authorization": f"Bearer {self.secret_key}"}

    async def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post(path, headers=self._headers(), data=data)
        if response.is_error:
            try:
                detail = response.json().get("error", {}).get("message", "Stripe request failed")
            except (ValueError, AttributeError):
                detail = "Stripe request failed"
            raise BillingProviderError(str(detail))
        return response.json()

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.get(path, headers=self._headers(), params=params)
        if response.is_error:
            try:
                detail = response.json().get("error", {}).get("message", "Stripe request failed")
            except (ValueError, AttributeError):
                detail = "Stripe request failed"
            raise BillingProviderError(str(detail))
        return response.json()

    async def create_customer(self, *, email: str, name: str, user_id: int) -> str:
        data = {
            "email": email,
            "name": name,
            "metadata[user_id]": str(user_id),
        }
        result = await self._post("/customers", data)
        return str(result["id"])

    async def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        plan_code: str,
        user_id: int,
        trial_days: int,
    ) -> CheckoutSession:
        data = {
            "mode": "subscription",
            "customer": customer_id,
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": self.success_url,
            "cancel_url": self.cancel_url,
            "client_reference_id": str(user_id),
            "metadata[user_id]": str(user_id),
            "metadata[plan_code]": plan_code,
            "subscription_data[metadata][user_id]": str(user_id),
            "subscription_data[metadata][plan_code]": plan_code,
        }
        if trial_days > 0:
            data["subscription_data[trial_period_days]"] = str(trial_days)
        result = await self._post("/checkout/sessions", data)
        return CheckoutSession(
            id=str(result["id"]),
            url=str(result["url"]),
            customer_id=customer_id,
            subscription_id=str(result["subscription"]) if result.get("subscription") else None,
        )

    async def create_portal_session(self, *, customer_id: str) -> str:
        result = await self._post("/billing_portal/sessions", {"customer": customer_id})
        return str(result["url"])

    async def list_invoices(self, *, customer_id: str, limit: int = 20) -> list[dict[str, Any]]:
        result = await self._get("/invoices", {"customer": customer_id, "limit": str(limit)})
        return list(result.get("data", []))

    @staticmethod
    def verify_webhook(payload: bytes, signature: str, secret: str, tolerance_seconds: int = 300) -> dict[str, Any]:
        if not secret:
            raise BillingProviderError("Stripe webhook secret is not configured.")
        timestamp: str | None = None
        signatures: list[str] = []
        for item in signature.split(","):
            key, _, value = item.partition("=")
            if key == "t":
                timestamp = value
            elif key == "v1":
                signatures.append(value)
        if not timestamp or not signatures:
            raise BillingProviderError("Invalid Stripe webhook signature.")
        try:
            timestamp_int = int(timestamp)
        except ValueError as exc:
            raise BillingProviderError("Invalid Stripe webhook timestamp.") from exc
        if abs(int(time.time()) - timestamp_int) > tolerance_seconds:
            raise BillingProviderError("Expired Stripe webhook signature.")
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
            raise BillingProviderError("Invalid Stripe webhook signature.")
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BillingProviderError("Invalid Stripe webhook payload.") from exc


def provider_for(name: str) -> StripeBillingProvider:
    if name != "stripe":
        raise BillingProviderError(f"Unsupported billing provider: {name}")
    return StripeBillingProvider()
