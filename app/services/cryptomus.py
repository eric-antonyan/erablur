"""Small, audited Cryptomus Merchant API client.

The client only creates hosted invoices and checks their status. Private keys,
wallet seeds and card details never pass through this application.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any

import httpx

from app.config.settings import settings


class CryptomusError(RuntimeError):
    pass


class CryptomusClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return settings.cryptomus_configured

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.cryptomus_base_url,
                timeout=settings.cryptomus_timeout,
                follow_redirects=False,
                headers={"Accept": "application/json"},
            )
        return self._client

    @staticmethod
    def _encode_body(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _signature(body: bytes) -> str:
        encoded = base64.b64encode(body).decode("ascii")
        return hashlib.md5((encoded + settings.cryptomus_payment_key).encode("utf-8")).hexdigest()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise CryptomusError("Cryptomus-ը կազմաձևված չէ։")
        body = self._encode_body(payload)
        client = await self._http()
        try:
            response = await client.post(
                path,
                content=body,
                headers={
                    "merchant": settings.cryptomus_merchant_id,
                    "sign": self._signature(body),
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CryptomusError(f"Cryptomus կապի սխալ՝ {exc}") from exc
        if not isinstance(data, dict) or int(data.get("state", 1)) != 0:
            message = data.get("message") if isinstance(data, dict) else None
            errors = data.get("errors") if isinstance(data, dict) else None
            raise CryptomusError(str(message or errors or "Cryptomus-ը մերժեց հարցումը։"))
        result = data.get("result")
        if not isinstance(result, dict):
            raise CryptomusError("Cryptomus-ի պատասխանը թերի է։")
        return result

    async def create_invoice(self, *, amount_usd: Decimal, order_id: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "amount": format(amount_usd.quantize(Decimal("0.01")), "f"),
            "currency": settings.cryptomus_invoice_currency,
            "order_id": order_id,
            "is_payment_multiple": True,
            "lifetime": settings.cryptomus_lifetime,
            "additional_data": order_id,
        }
        if settings.cryptomus_to_currency:
            payload["to_currency"] = settings.cryptomus_to_currency
        if settings.cryptomus_network:
            payload["network"] = settings.cryptomus_network
        if settings.cryptomus_callback_url:
            payload["url_callback"] = settings.cryptomus_callback_url
        if settings.cryptomus_return_url:
            payload["url_return"] = settings.cryptomus_return_url
        if settings.cryptomus_success_url:
            payload["url_success"] = settings.cryptomus_success_url
        return await self._post("/v1/payment", payload)

    async def payment_info(self, *, order_id: str) -> dict[str, Any]:
        return await self._post("/v1/payment/info", {"order_id": order_id})

    @staticmethod
    def verify_webhook(payload: dict[str, Any]) -> bool:
        received = str(payload.get("sign") or "")
        if not received or not settings.cryptomus_payment_key:
            return False
        unsigned = dict(payload)
        unsigned.pop("sign", None)
        serializations = {
            json.dumps(unsigned, ensure_ascii=False, separators=(",", ":")),
            json.dumps(unsigned, ensure_ascii=False, separators=(",", ":")).replace("/", "\\/"),
        }
        for serialized in serializations:
            encoded = base64.b64encode(serialized.encode("utf-8")).decode("ascii")
            expected = hashlib.md5((encoded + settings.cryptomus_payment_key).encode("utf-8")).hexdigest()
            if hmac.compare_digest(expected, received):
                return True
        return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


cryptomus = CryptomusClient()
