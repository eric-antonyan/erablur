<<<<<<< HEAD
from aiogram import Router, types, F
from loguru import logger
from bson import ObjectId
from app.db.mongo import channels_collection

router = Router()

# ---------------------
# ⚙️ CALLBACK PREFIX
# ---------------------
CB_PREFIX = "channel_manage"


# ---------------------
# 🔹 OPEN MANAGEMENT PANEL
# ---------------------
@router.callback_query(F.data == "manage_channels")
async def open_manage_panel(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    channels = [ch async for ch in channels_collection.find({"owner_id": user_id})]
    keyboard = []
    if not channels:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Միացնել նոր ալիք", callback_data="connect_info")],
            [types.InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="back_to_menu")],
        ])

        await cb.message.answer(
            "❌ Դուք դեռ չեք միացրել ոչ մի ալիք։\n\n"
            "📡 Կարող եք միացնել նոր ալիք՝ /start հրամանով։",
            reply_markup=keyboard,
        )
        await cb.answer()
        return

    keyboard = []
    for ch in channels:
        title = ch.get("title", "Անանուն ալիք")
        cid = str(ch["channel_id"])
        keyboard.append([
            types.InlineKeyboardButton(text=f"📢 {title}", callback_data=f"{CB_PREFIX}|show|{cid}")
        ])

    keyboard.append([
        types.InlineKeyboardButton(text="➕ Միացնել նոր ալիք", callback_data="connect_info")
    ])
    keyboard.append([
        types.InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="back_to_menu")
    ])

    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await cb.message.answer(
        "⚙️ Ձեր միացված ալիքները․\n\n"
        "Ընտրեք ցանկից ալիքը՝ ավելին տեսնելու կամ անջատելու համար։",
        reply_markup=kb
    )
    await cb.answer()


# ---------------------
# 🔹 SHOW CHANNEL INFO
# ---------------------
@router.callback_query(F.data.startswith(f"{CB_PREFIX}|show|"))
async def show_channel_info(cb: types.CallbackQuery):
    try:
        _, _, cid = cb.data.split("|", 2)
    except Exception as e:
        logger.warning(f"⚠️ Bad channel show callback: {cb.data}")
        await cb.answer("Սխալ տվյալ։", show_alert=True)
        return

    channel = await channels_collection.find_one({"channel_id": int(cid)})
    if not channel:
        await cb.message.answer("❌ Ալիքը այլևս չկա կամ արդեն անջատվել է։")
        await cb.answer()
        return

    title = channel.get("title", "Անանուն ալիք")
    owner_id = channel.get("owner_id")
    connected_at = channel.get("connected_at", "Անհայտ")

    text = (
        f"📢 <b>{title}</b>\n"
        f"👤 Հասցեատեր․ <code>{owner_id}</code>\n"
        f"📅 Միացվել է՝ {connected_at}\n\n"
        "Կարող եք անջատել ալիքը, որպեսզի բոտը դադարեցնի հրապարակումները։"
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Անջատել բոտը", callback_data=f"{CB_PREFIX}|disconnect|{cid}")],
        [types.InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="manage_channels")],
    ])

    await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


# ---------------------
# 🔹 DISCONNECT CHANNEL
# ---------------------
@router.callback_query(F.data.startswith(f"{CB_PREFIX}|disconnect|"))
async def disconnect_channel(cb: types.CallbackQuery):
    try:
        _, _, cid = cb.data.split("|", 2)
    except Exception as e:
        logger.warning(f"⚠️ Bad disconnect callback: {cb.data}")
        await cb.answer("Սխալ տվյալ։", show_alert=True)
        return

    result = await channels_collection.delete_one({"channel_id": int(cid)})

    if result.deleted_count:
        await cb.message.answer("✅ Ալիքը հաջողությամբ անջատվեց։")
        logger.info(f"🧹 Channel {cid} disconnected by user {cb.from_user.id}")
    else:
        await cb.message.answer("⚠️ Ալիքը արդեն անջատված էր։")

    await cb.answer()

@router.message(F.chat_shared)
async def handle_channel_shared(message: types.Message):
    shared = message.chat_shared
    chat_id = shared.chat_id
    user_id = message.from_user.id

    try:
        chat = await message.bot.get_chat(chat_id)

        await channels_collection.update_one(
            {"channel_id": chat_id},
            {"$set": {
                "title": chat.title,
                "owner_id": user_id,
                "connected_at": message.date
            }},
            upsert=True,
        )

        await message.answer(
            f"✅ Ալիքը հաջողությամբ միացվեց՝ <b>{chat.title}</b>։",
            parse_mode="HTML",
        )

    except Exception as e:
        await message.answer(
            "⚠️ Խնդրում եմ համոզվեք, որ բոտը ավելացված է ձեր ալիք որպես ադմինիստրատոր։"
        )
        print(f"Error saving channel: {e}")
=======
from __future__ import annotations

import html

from aiogram import F, Router, types
from aiogram.types import ReplyKeyboardRemove
from loguru import logger

from app.db.database import db

router = Router(name="channel_manage")
CB_PREFIX = "channel_manage"


@router.callback_query(F.data.startswith(f"{CB_PREFIX}|show|"))
async def show_channel_info(callback: types.CallbackQuery) -> None:
    try:
        channel_id = int(callback.data.rsplit("|", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Սխալ տվյալ։", show_alert=True)
        return
    channel = db.get_channel(channel_id)
    if not channel:
        await callback.answer("Ալիքը չի գտնվել։", show_alert=True)
        return
    title = html.escape(str(channel.get("title") or "Անանուն ալիք"))
    connected_at = html.escape(str(channel.get("connected_at") or "անհայտ"))
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Անջատել", callback_data=f"{CB_PREFIX}|disconnect|{channel_id}")],
        [types.InlineKeyboardButton(text="↩️ Իմ ալիքները", callback_data="manage_channels")],
    ])
    await callback.message.answer(
        f"📢 <b>{title}</b>\n"
        f"🆔 <code>{channel_id}</code>\n"
        f"📅 Միացվել է՝ {connected_at}\n\n"
        "Բոտը այս ալիքում կհրապարակի ամենօրյա հիշատակի գրառումներ։",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_PREFIX}|disconnect|"))
async def disconnect_channel(callback: types.CallbackQuery) -> None:
    try:
        channel_id = int(callback.data.rsplit("|", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Սխալ տվյալ։", show_alert=True)
        return
    deleted = db.delete_channel(channel_id)
    await callback.message.answer("✅ Ալիքը անջատվեց։" if deleted else "Ալիքը արդեն անջատված էր։")
    logger.info("Channel {} disconnected by user {}", channel_id, callback.from_user.id)
    await callback.answer()


@router.message(F.chat_shared)
async def handle_channel_shared(message: types.Message) -> None:
    shared = message.chat_shared
    user_id = str(message.from_user.id)
    try:
        chat = await message.bot.get_chat(shared.chat_id)
        member = await message.bot.get_chat_member(shared.chat_id, (await message.bot.get_me()).id)
        if member.status not in {"administrator", "creator"}:
            await message.answer(
                "⚠️ Նախ ավելացրեք բոտը ալիքում որպես ադմինիստրատոր՝ հաղորդագրություններ հրապարակելու իրավունքով։",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        db.save_channel(shared.chat_id, chat.title or str(shared.chat_id), user_id)
        await message.answer(
            f"✅ Ալիքը միացվեց՝ <b>{html.escape(chat.title or str(shared.chat_id))}</b>։\n\n"
            "Ամենօրյա հրապարակումները կաշխատեն ըստ .env-ում նշված ժամի։",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as exc:
        logger.warning("Channel connect failed: {}", exc)
        await message.answer(
            "⚠️ Չհաջողվեց միացնել ալիքը։ Ստուգեք, որ բոտը ալիքի ադմինիստրատոր է և կարող է հաղորդագրություններ հրապարակել։",
            reply_markup=ReplyKeyboardRemove(),
        )
>>>>>>> 54c1deb (commit)
