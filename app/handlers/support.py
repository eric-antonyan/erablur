from __future__ import annotations

import asyncio
import html
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from loguru import logger

from app.config.settings import settings
from app.db.database import db
from app.services.cryptomus import CryptomusError, cryptomus

router = Router(name="support")

PAID_CRYPTO_STATUSES = {"paid", "paid_over"}
FINAL_FAILED_STATUSES = {"fail", "cancel", "system_fail", "refund_fail", "refund_paid"}


class SupportStates(StatesGroup):
    waiting_crypto_amount = State()


def _order_id(prefix: str) -> str:
    # Cryptomus order IDs accept letters, numbers, underscores and dashes.
    return f"{prefix}_{uuid4().hex[:22]}"


def _support_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append([InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="support_stars")])
    if settings.cryptomus_configured:
        rows.append([InlineKeyboardButton(text="💎 USDT / Crypto (Cryptomus)", callback_data="support_crypto")])
    # if settings.bank_card_payment_url.startswith("https://"):
    #     rows.append([InlineKeyboardButton(text=settings.bank_card_label, url=settings.bank_card_payment_url)])
    for method in settings.extra_payment_methods:
        rows.append([InlineKeyboardButton(text=method["title"], url=method["url"])])
    rows.extend([
        [
            InlineKeyboardButton(text="🧾 Իմ աջակցությունները", callback_data="support_history"),
            InlineKeyboardButton(text="🔐 Գաղտնիություն", callback_data="support_terms"),
        ],
        [InlineKeyboardButton(text="↩️ Գլխավոր մենյու", callback_data="back_to_menu")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _stars_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for amount in settings.stars_amounts:
        pair.append(InlineKeyboardButton(text=f"⭐ {amount}", callback_data=f"support_star|{amount}"))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton(text="↩️ Աջակցության բաժին", callback_data="support_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _crypto_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    # pair: list[InlineKeyboardButton] = []
    # for amount in settings.crypto_amounts_usd:
    #     pair.append(InlineKeyboardButton(text=f"${amount}", callback_data=f"support_crypto_amount|{amount}"))
    #     if len(pair) == 2:
    #         rows.append(pair)
    #         pair = []
    # if pair:
    #     rows.append(pair)
    rows.extend([
        # [InlineKeyboardButton(text="✍️ Այլ գումար", callback_data="support_crypto_custom")],
        [InlineKeyboardButton(text="↩️ Աջակցության բաժին", callback_data="support_home")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _history_status(status: str) -> str:
    return {
        "pending": "⏳ սպասում է",
        "check": "🔄 ստուգվում է",
        "confirm_check": "🔄 հաստատվում է",
        "paid": "✅ վճարված",
        "paid_over": "✅ վճարված (+)",
        "completed": "✅ վճարված",
        "wrong_amount": "⚠️ սխալ գումար",
        "cancel": "❌ չեղարկված",
        "fail": "❌ ձախողված",
        "system_fail": "❌ համակարգային սխալ",
        "create_failed": "❌ invoice չի ստեղծվել",
        "refund_process": "↩️ վերադարձվում է",
        "refund_paid": "↩️ վերադարձված",
    }.get(status, f"ℹ️ {status}")


async def _ensure_support_enabled(event: types.Message | types.CallbackQuery) -> bool:
    if settings.support_enabled:
        return True
    if isinstance(event, types.CallbackQuery):
        await event.answer("Աջակցության բաժինը ժամանակավորապես անջատված է։", show_alert=True)
    else:
        await event.answer("Աջակցության բաժինը ժամանակավորապես անջատված է։")
    return False


async def _show_support(message: types.Message, *, edit: bool = False) -> None:
    if not settings.support_enabled:
        if edit:
            try:
                await message.edit_text("Աջակցության բաժինը ժամանակավորապես անջատված է։")
                return
            except Exception:
                pass
        await message.answer("Աջակցության բաժինը ժամանակավորապես անջատված է։")
        return
    text = (
        f"❤️ <b>Աջակցել «{html.escape(settings.support_project_name)}» նախագծին</b>\n\n"
        "Ձեր աջակցությունն օգնում է պահպանել հերոսների կենսագրությունները, զարգացնել որոնումը, "
        "AI օգնականը և նախագծի տեխնիկական ենթակառուցվածքը։\n\n"
        "🔒 Բոտը հանրայնորեն չի ցուցադրում աջակցողի անունը կամ username-ը։ "
        "Քարտի և wallet-ի տվյալները բոտը չի ստանում և չի պահում։\n\n"
        f"<i>{html.escape(settings.support_note)}</i>"
    )
    if edit:
        try:
            await message.edit_text(text, parse_mode="HTML", reply_markup=_support_keyboard())
            return
        except Exception:
            pass
    await message.answer(text, parse_mode="HTML", reply_markup=_support_keyboard())


@router.message(Command("support", "donate"))
async def support_command(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await _show_support(message)


@router.callback_query(F.data == "support_home")
async def support_home(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_support(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data == "support_stars")
async def support_stars(callback: types.CallbackQuery) -> None:
    text = (
        "⭐ <b>Աջակցություն Telegram Stars-ով</b>\n\n"
        "Վճարումն իրականացվում է Telegram-ի invoice պատուհանում։ Բոտը չի պահանջում անուն, "
        "հեռախոս, էլ․ հասցե կամ քարտի տվյալներ։\n\nԸնտրեք Stars-ի քանակը։"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_stars_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("support_star|"))
async def create_stars_invoice(callback: types.CallbackQuery) -> None:
    if not await _ensure_support_enabled(callback):
        return
    try:
        amount = int(callback.data.split("|", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Սխալ գումար։", show_alert=True)
        return
    if amount not in settings.stars_amounts:
        await callback.answer("Այս գումարը թույլատրված չէ։", show_alert=True)
        return
    order_id = _order_id("star")
    db.create_donation(
        order_id,
        user_id=callback.from_user.id,
        provider="telegram_stars",
        amount=str(amount),
        currency="XTR",
        anonymous=True,
    )
    payload = f"support|{order_id}|{amount}"
    try:
        await callback.message.answer_invoice(
            title=f"Աջակցություն՝ {settings.support_project_name}",
            description="Կամավոր աջակցություն նախագծի պահպանման և զարգացման համար։",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label="Կամավոր աջակցություն", amount=amount)],
            provider_token="",
            start_parameter=f"support-{order_id}",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            protect_content=True,
        )
    except Exception as exc:
        db.update_donation(order_id, status="create_failed")
        logger.warning("Could not create Stars invoice {}: {}", order_id, exc)
        await callback.answer("Stars invoice-ը չստեղծվեց։", show_alert=True)
        return
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(query: types.PreCheckoutQuery) -> None:
    if not settings.support_enabled:
        await query.answer(ok=False, error_message="Աջակցության բաժինը ժամանակավորապես անջատված է։")
        return
    payload = query.invoice_payload or ""
    parts = payload.split("|")
    if len(parts) != 3 or parts[0] != "support":
        await query.answer(ok=False, error_message="Invoice-ը չի ճանաչվել։")
        return
    order_id, expected_raw = parts[1], parts[2]
    donation = db.get_donation(order_id)
    try:
        expected = int(expected_raw)
    except ValueError:
        expected = -1
    valid = bool(
        donation
        and donation.get("provider") == "telegram_stars"
        and str(donation.get("user_id")) == str(query.from_user.id)
        and query.currency == "XTR"
        and query.total_amount == expected
        and str(donation.get("status")) == "pending"
    )
    if not valid:
        await query.answer(ok=False, error_message="Invoice-ի տվյալները չեն համապատասխանում։")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    parts = (payment.invoice_payload or "").split("|")
    if len(parts) != 3 or parts[0] != "support":
        logger.warning("Unknown successful payment payload: {}", payment.invoice_payload)
        return
    order_id = parts[1]
    donation = db.get_donation(order_id)
    already_notified = bool(donation and donation.get("notified_at"))
    if not donation:
        db.create_donation(
            order_id,
            user_id=message.from_user.id,
            provider="telegram_stars",
            amount=str(payment.total_amount),
            currency=payment.currency,
            anonymous=True,
        )
    db.update_donation(
        order_id,
        status="completed",
        telegram_charge_id=payment.telegram_payment_charge_id,
        paid_amount=str(payment.total_amount),
        paid_currency=payment.currency,
        mark_paid=True,
    )
    if already_notified:
        return
    db.mark_donation_notified(order_id)
    await message.answer(
        "✅ <b>Աջակցությունը հաստատվեց</b>\n\n"
        f"Գումար՝ <b>⭐ {payment.total_amount}</b>\n\n"
        "Շնորհակալություն «Հայոց Հերոսներ» նախագծին աջակցելու համար։ "
        "Ձեր անունը հանրայնորեն չի ցուցադրվի։ 🇦🇲",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❤️ Աջակցության բաժին", callback_data="support_home")],
            [InlineKeyboardButton(text="↩️ Գլխավոր մենյու", callback_data="back_to_menu")],
        ]),
    )


@router.callback_query(F.data == "support_crypto")
async def support_crypto(callback: types.CallbackQuery) -> None:
    # if not settings.cryptomus_configured:
    #     await callback.answer("Cryptomus-ը դեռ կազմաձևված չէ։", show_alert=True)
    #     return
    # network_text = f" ({settings.cryptomus_network.upper()})" if settings.cryptomus_network else ""
    # text = (
    #     "💎 <b>USDT / Crypto աջակցություն</b>\n\n"
    #     f"Invoice-ը ստեղծվում է Cryptomus-ում՝ {html.escape(settings.cryptomus_to_currency)}{network_text} վճարման համար։ "
    #     "Վճարման էջում կարող են հասանելի լինել նաև այլ կրիպտոարժույթներ կամ ցանցեր՝ ըստ ձեր merchant կարգավորումների։\n\n"
    #     "Բոտը չի պահանջում անուն կամ wallet seed phrase։ Ընտրեք USD համարժեքը։"
    # )
    text = "Сrypto վճարումները այս պահին հասանելի չեն։ Շնորհակալություն։"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_crypto_keyboard())
    await callback.answer()


async def _create_crypto_invoice(message: types.Message, user_id: int, amount: Decimal) -> None:
    if not settings.support_enabled:
        await message.answer("Աջակցության բաժինը ժամանակավորապես անջատված է։")
        return
    minimum = Decimal(str(settings.crypto_min_usd))
    maximum = Decimal(str(settings.crypto_max_usd))
    if not amount.is_finite() or amount < minimum or amount > maximum:
        await message.answer(f"Գումարը պետք է լինի {minimum}–{maximum} USD միջակայքում։")
        return
    order_id = _order_id("crypto")
    amount_text = format(amount.quantize(Decimal("0.01")), "f")
    db.create_donation(
        order_id,
        user_id=user_id,
        provider="cryptomus",
        amount=amount_text,
        currency=settings.cryptomus_invoice_currency,
        anonymous=True,
    )
    wait = await message.answer("⏳ Ստեղծվում է անվտանգ Cryptomus invoice-ը…")
    try:
        result = await cryptomus.create_invoice(amount_usd=amount, order_id=order_id)
    except CryptomusError as exc:
        db.update_donation(order_id, status="create_failed")
        await wait.edit_text(
            "❌ Invoice-ը չստեղծվեց։\n\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Կրկին փորձել", callback_data="support_crypto")]
            ]),
        )
        return

    payment_url = str(result.get("url") or "")
    status = str(result.get("payment_status") or "pending")
    db.update_donation(
        order_id,
        status=status,
        provider_payment_id=str(result.get("uuid") or ""),
        invoice_url=payment_url,
        network=str(result.get("network") or ""),
    )
    rows: list[list[InlineKeyboardButton]] = []
    if payment_url.startswith(("https://", "http://")):
        rows.append([InlineKeyboardButton(text="💳 Բացել վճարման էջը", url=payment_url)])
    rows.append([InlineKeyboardButton(text="🔄 Ստուգել վճարումը", callback_data=f"support_check|{order_id}")])
    rows.append([InlineKeyboardButton(text="↩️ Աջակցության բաժին", callback_data="support_home")])
    await wait.edit_text(
        "💎 <b>Cryptomus invoice-ը պատրաստ է</b>\n\n"
        f"Գումար՝ <b>${html.escape(amount_text)}</b>\n"
        f"Նպատակային արժույթ՝ <b>{html.escape(settings.cryptomus_to_currency or 'Crypto')}</b>\n"
        f"Պատվեր՝ <code>{order_id}</code>\n\n"
        "Բացեք վճարման էջը։ Վճարումից հետո սեղմեք «Ստուգել վճարումը»։",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("support_crypto_amount|"))
async def create_crypto_preset(callback: types.CallbackQuery) -> None:
    if not settings.cryptomus_configured:
        await callback.answer("Cryptomus-ը կազմաձևված չէ։", show_alert=True)
        return
    try:
        amount = Decimal(callback.data.split("|", 1)[1])
    except (InvalidOperation, IndexError):
        await callback.answer("Սխալ գումար։", show_alert=True)
        return
    await callback.answer()
    await _create_crypto_invoice(callback.message, callback.from_user.id, amount)


@router.callback_query(F.data == "support_crypto_custom")
async def ask_crypto_custom(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportStates.waiting_crypto_amount)
    await callback.message.answer(
        f"Գրեք գումարը USD-ով՝ {settings.crypto_min_usd:g}–{settings.crypto_max_usd:g} միջակայքում։\n"
        "Օրինակ՝ <code>15</code> կամ <code>27.50</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SupportStates.waiting_crypto_amount)
async def receive_crypto_custom(message: types.Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".").replace("$", "")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await message.answer("Գրեք միայն թիվ, օրինակ՝ <code>15</code>։", parse_mode="HTML")
        return
    minimum = Decimal(str(settings.crypto_min_usd))
    maximum = Decimal(str(settings.crypto_max_usd))
    if not amount.is_finite() or amount < minimum or amount > maximum:
        await message.answer(f"Գումարը պետք է լինի {minimum}–{maximum} USD միջակայքում։")
        return
    await state.clear()
    await _create_crypto_invoice(message, message.from_user.id, amount)


@router.callback_query(F.data.startswith("support_check|"))
async def check_crypto_payment(callback: types.CallbackQuery) -> None:
    order_id = callback.data.split("|", 1)[1]
    donation = db.get_donation(order_id)
    if not donation:
        await callback.answer("Պատվերը չի գտնվել։", show_alert=True)
        return
    if str(donation.get("user_id")) != str(callback.from_user.id) and callback.from_user.id not in settings.admin_ids:
        await callback.answer("Այս պատվերը ձեզ չի պատկանում։", show_alert=True)
        return
    if donation.get("provider") != "cryptomus":
        await callback.answer("Սխալ provider։", show_alert=True)
        return
    await callback.answer("Ստուգվում է…")
    try:
        result = await cryptomus.payment_info(order_id=order_id)
    except CryptomusError as exc:
        await callback.message.answer(f"Ստուգման սխալ՝ <code>{html.escape(str(exc))}</code>", parse_mode="HTML")
        return
    status = str(result.get("payment_status") or result.get("status") or "pending")
    paid = status in PAID_CRYPTO_STATUSES
    db.update_donation(
        order_id,
        status=status,
        provider_payment_id=str(result.get("uuid") or ""),
        invoice_url=str(result.get("url") or ""),
        paid_amount=str(result.get("payment_amount") or ""),
        paid_currency=str(result.get("payer_currency") or result.get("currency") or ""),
        network=str(result.get("network") or ""),
        txid=str(result.get("txid") or ""),
        mark_paid=paid,
    )
    if paid:
        if donation.get("notified_at"):
            await callback.message.answer("✅ Այս աջակցությունն արդեն հաստատված է։ Շնորհակալություն։ 🇦🇲")
            return
        db.mark_donation_notified(order_id)
        await callback.message.answer(
            "✅ <b>Աջակցությունը հաստատվեց</b>\n\n"
            f"Գումար՝ <b>{html.escape(str(result.get('payment_amount') or donation.get('amount')))} "
            f"{html.escape(str(result.get('payer_currency') or donation.get('currency')))}</b>\n\n"
            "Շնորհակալություն «Հայոց Հերոսներ» նախագծին աջակցելու համար։ 🇦🇲",
            parse_mode="HTML",
        )
    elif status == "wrong_amount":
        await callback.message.answer(
            "⚠️ Վճարված գումարը չի համապատասխանում invoice-ին։ Բացեք նույն invoice-ը և լրացրեք պակասող գումարը, եթե այն դեռ ակտիվ է։"
        )
    elif status in FINAL_FAILED_STATUSES:
        await callback.message.answer(f"❌ Վճարումը չի ավարտվել։ Կարգավիճակ՝ <code>{html.escape(status)}</code>", parse_mode="HTML")
    else:
        await callback.message.answer(
            f"⏳ Վճարումը դեռ չի հաստատվել։ Կարգավիճակ՝ <code>{html.escape(status)}</code>\n"
            "Մի փոքր անց կրկին սեղմեք ստուգման կոճակը։",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "support_history")
async def support_history(callback: types.CallbackQuery) -> None:
    donations = await asyncio.to_thread(db.get_user_donations, callback.from_user.id, 15)
    if not donations:
        text = "🧾 Դուք դեռ գրանցված աջակցություն չունեք։"
    else:
        lines = ["🧾 <b>Ձեր վերջին աջակցությունները</b>\n"]
        for item in donations:
            provider = "Stars" if item.get("provider") == "telegram_stars" else "Cryptomus"
            lines.append(
                f"• {html.escape(str(item.get('amount')))} {html.escape(str(item.get('currency')))} · "
                f"{provider} · {html.escape(_history_status(str(item.get('status'))))}"
            )
        text = "\n".join(lines)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Աջակցության բաժին", callback_data="support_home")]
        ]),
    )
    await callback.answer()


TERMS_TEXT = (
    "🔐 <b>Աջակցության և գաղտնիության պայմաններ</b>\n\n"
    "• Աջակցությունը կամավոր է և որևէ վճարովի գործառույթ չի բացում։\n"
    "• Աջակցողի անունը և username-ը հանրայնորեն չեն ցուցադրվում։\n"
    "• Բոտը պահում է նվազագույն տեխնիկական տվյալներ՝ Telegram user ID, order ID, գումար, կարգավիճակ և provider transaction ID։ "
    "Դրանք անհրաժեշտ են կրկնակի վճարումները կանխելու, վճարումը ստուգելու և վերադարձի/վեճի հարցերը լուծելու համար։\n"
    "• Բոտը չի ստանում կամ պահում քարտի համարը, CVV-ն, wallet seed phrase-ը կամ private key-ը։\n"
    "• Telegram-ը, բանկը, app store-ը, Cryptomus-ը կամ այլ վճարային provider-ը կարող են տեսնել գործարքի տվյալները և պահանջել նույնականացում՝ իրենց կանոնների համաձայն։\n"
    "• Կրիպտո փոխանցումները կարող են լինել անդառնալի։ Միշտ ստուգեք ցանցը, արժույթը և գումարը։\n"
    "• Վճարման խնդրի դեպքում օգտագործեք /paysupport հրամանը։"
)


@router.callback_query(F.data == "support_terms")
async def support_terms_callback(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        TERMS_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Աջակցության բաժին", callback_data="support_home")]
        ]),
    )
    await callback.answer()


@router.message(Command("terms"))
async def terms_command(message: types.Message) -> None:
    await message.answer(TERMS_TEXT, parse_mode="HTML")


@router.message(Command("paysupport"))
async def payment_support_command(message: types.Message) -> None:
    contact = settings.support_contact
    contact_line = (
        f"Կապ՝ {html.escape(contact)}" if contact else "Կապի հասցեն դեռ չի կազմաձևվել։ Դիմեք բոտի ադմինիստրատորին։"
    )
    await message.answer(
        "🛟 <b>Վճարումների աջակցություն</b>\n\n"
        "Նամակում նշեք միայն order ID-ն և խնդրի նկարագրությունը։ Մի ուղարկեք քարտի ամբողջ համարը, CVV, password, seed phrase կամ private key։\n\n"
        f"{contact_line}\n\n"
        "Telegram-ի կամ Cryptomus-ի աջակցությունը չի կառավարում այս բոտի պատվերները։",
        parse_mode="HTML",
    )
