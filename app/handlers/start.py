from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from bson import ObjectId
from urllib.parse import unquote
from loguru import logger
import re

from app.db.redis_db import cache
from app.db.mongo import users_collection, heroes_collection
from app.utils.cache import set_cached_hero
from app.handlers.museum_search import build_caption, build_keyboard

router = Router()


# -----------------------------
# /start handler (with deep links)
# -----------------------------
@router.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    # --- Redis fast cache ---
    user_key = f"user:{user_id}"
    cache.hset(
        user_key,
        mapping={
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        },
    )
    cache.sadd("users:set", user_id)

    # --- Mongo persistent storage ---
    existing = await users_collection.find_one({"id": user_id})
    if not existing:
        await users_collection.insert_one({
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "joined_at": message.date,
        })

    # --- Build main menu keyboard ---
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏛️ Թանգարան", callback_data="museum"),
            InlineKeyboardButton(text="⚔️ Որոնել հերոս", switch_inline_query_current_chat="")
        ],
        [
            InlineKeyboardButton(text="📈 Իմ պրոֆիլը", callback_data="profile"),
            InlineKeyboardButton(text="📜 Մեր մասին", callback_data="about")
        ],
        [
            InlineKeyboardButton(text="📡 Իմ ալիքները", callback_data="manage_channels")
        ]
    ])

    # --- Parse /start argument ---
    args = message.text.split(maxsplit=1)

    # No argument (normal /start)
    if len(args) == 1:
        await message.answer(
            "🇦🇲 Բարի գալուստ Հայկական հերոսների թանգարան 🕊️\n\n"
            "Ընտրեք ստորև ներկայացված տարբերակներից՝ սկսելու համար։",
            reply_markup=kb,
        )
        return

    # Has argument
    param = args[1].strip()
    decoded = unquote(param)

    # 🧠 Check if it's a hero deep link (24-char hex id)
    match = re.search(r"[0-9a-f]{24}$", decoded)
    if not match:
        logger.warning(f"Ignored non-hero start parameter: {decoded}")
        await message.answer(
            "🇦🇲 Բարի գալուստ Հայկական հերոսների թանգարան 🕊️\n\n"
            "Այս հղումը չի պարունակում հերոսի տվյալներ։",
            reply_markup=kb,
        )
        return

    hero_id = match.group(0)
    wait_message = await message.answer("Սպասել․․․")

    try:
        hero = await heroes_collection.find_one({"_id": ObjectId(hero_id)})
    except Exception as e:
        logger.warning(f"Invalid start parameter: {param} ({e})")
        await wait_message.edit_text("⚠️ Հղումը անվավեր է կամ հերոսը չի գտնվել։")
        return

    if not hero:
        await wait_message.edit_text("❌ Այդ հղումով հերոս չի գտնվել։")
        return

    # Build hero display with pagination
    all_heroes = [h async for h in heroes_collection.find()]
    total = len(all_heroes)
    current_index = next(
        (i for i, h in enumerate(all_heroes) if str(h["_id"]) == hero_id), 0
    )

    # Cache hero list for pagination
    cache_key = f"hero:{hero_id}"
    set_cached_hero(cache_key, [str(h["_id"]) for h in all_heroes])

    caption = build_caption(hero, current_index, total)
    keyboard = build_keyboard("all", current_index, total, cache_key)

    try:
        await wait_message.delete()
        await message.answer_photo(
            hero["img_url"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception:
        await message.answer(caption, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "connect_info")
async def show_connect_info(cb: types.CallbackQuery):
    description = (
        "📢 Երբ դուք միացնեք ձեր ալիքը՝ բոտը շաբաթվա ընթացքում ավտոմատ կերպով կհրապարակի "
        "հայ հերոսների մասին հիշատակի գրառումներ ձեր ալիքում։\n\n"
        "⚙️ Բոտը կօգտագործի միայն ձեր թույլատրությունը հրապարակումներ կատարելու համար։\n\n"
        "Սեղմեք ներքևի կոճակը՝ ալիքը միացնելու համար։"
    )

    # create the Telegram channel-sharing button
    connect_button = KeyboardButton(
    text="📡 Կապել ալիք",
    request_chat=types.KeyboardButtonRequestChat(
        request_id=1,
        chat_is_channel=True,
        chat_is_created=True
    ),
)


    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[connect_button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await cb.message.answer(description, reply_markup=reply_kb)
    await cb.answer()
        