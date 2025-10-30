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
