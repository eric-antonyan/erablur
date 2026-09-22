"""Optional local HTTP server for verified Cryptomus callbacks."""
from __future__ import annotations

import html
from typing import Any

from aiogram import Bot
from aiohttp import web
from loguru import logger

from app.config.settings import settings
from app.db.database import db
from app.services.cryptomus import cryptomus


PAID_STATUSES = {"paid", "paid_over"}


class PaymentWebhookServer:
    def __init__(self) -> None:
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._bot: Bot | None = None

    async def start(self, bot: Bot) -> None:
        if not settings.webhook_configured:
            return
        self._bot = bot
        app = web.Application(client_max_size=128 * 1024)
        path = f"/cryptomus/{settings.payment_webhook_path_secret}"
        app.router.add_post(path, self._handle_cryptomus)
        app.router.add_get("/health", self._health)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(
            self._runner,
            host=settings.payment_webhook_host,
            port=settings.payment_webhook_port,
        )
        await self._site.start()
        logger.info("Payment webhook listening on {}:{}{}", settings.payment_webhook_host, settings.payment_webhook_port, path)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
        self._runner = None
        self._site = None
        self._bot = None

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    async def _handle_cryptomus(self, request: web.Request) -> web.Response:
        if settings.cryptomus_verify_ip:
            remote = request.remote or ""
            if remote != "91.227.144.54":
                logger.warning("Rejected Cryptomus webhook from IP {}", remote)
                raise web.HTTPForbidden(text="forbidden")
        try:
            payload: Any = await request.json()
        except Exception:
            raise web.HTTPBadRequest(text="invalid json")
        if not isinstance(payload, dict) or not cryptomus.verify_webhook(payload):
            logger.warning("Rejected Cryptomus webhook with invalid signature")
            raise web.HTTPForbidden(text="invalid signature")

        order_id = str(payload.get("order_id") or "")
        if not order_id:
            raise web.HTTPBadRequest(text="missing order_id")
        donation = db.get_donation(order_id)
        if not donation:
            logger.warning("Webhook references unknown order {}", order_id)
            return web.json_response({"ok": True})

        status = str(payload.get("status") or "unknown")
        db.update_donation(
            order_id,
            status=status,
            provider_payment_id=str(payload.get("uuid") or ""),
            paid_amount=str(payload.get("payment_amount") or ""),
            paid_currency=str(payload.get("payer_currency") or payload.get("currency") or ""),
            network=str(payload.get("network") or ""),
            txid=str(payload.get("txid") or ""),
            mark_paid=status in PAID_STATUSES,
        )
        if status in PAID_STATUSES and not donation.get("notified_at") and self._bot is not None:
            try:
                await self._bot.send_message(
                    int(donation["user_id"]),
                    "✅ <b>Աջակցությունը հաստատվեց</b>\n\n"
                    f"Գումար՝ <b>{html.escape(str(payload.get('payment_amount') or donation.get('amount')))} "
                    f"{html.escape(str(payload.get('payer_currency') or donation.get('currency')))}</b>\n\n"
                    "Շնորհակալություն «Հայոց Հերոսներ» նախագծին աջակցելու համար։ 🇦🇲",
                    parse_mode="HTML",
                )
                db.mark_donation_notified(order_id)
            except Exception as exc:
                logger.warning("Could not notify donor for {}: {}", order_id, exc)
        return web.json_response({"ok": True})


payment_webhook = PaymentWebhookServer()
