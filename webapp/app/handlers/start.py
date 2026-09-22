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
import os

from app.db.redis_db import cache
from app.db.mongo import users_collection, heroes_collection
from app.utils.cache import set_cached_hero
from app.handlers.museum_search import build_caption, build_keyboard
from app.utils.util import compose_hero_image

router = Router()


def fix_unclosed_tags(text: str) -> str:
    text = re.sub(r"<[^>]*$", "", text)
    for tag in ("b", "i"):
        opens, closes = text.count(f"<{tag}>"), text.count(f"</{tag}>")
        if opens > closes:
            text += f"</{tag}>" * (opens - closes)
    return text


@router.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    # --- Redis fast cache (async!) ---
    user_key = f"user:{user_id}"
    await cache.hset(
        user_key,
        mapping={
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        },
    )
    await cache.sadd("users:set", user_id)

    # --- Mongo persistent storage ---
    existing = await users_collection.find_one({"id": user_id})
    if not existing:
        await users_collection.insert_one(
            {
                "id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "joined_at": message.date,
            }
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏛️ Թանգարան", callback_data="museum"),
                InlineKeyboardButton(
                    text="⚔️ Որոնել հերոս", switch_inline_query_current_chat=""
                ),
            ],
            [
                InlineKeyboardButton(text="📈 Իմ պրոֆիլը", callback_data="profile"),
                InlineKeyboardButton(text="📜 Մեր մասին", callback_data="about"),
            ],
            [InlineKeyboardButton(text="📡 Իմ ալիքները", callback_data="manage_channels")],
        ]
    )

    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        await message.answer(
            "🇦🇲 Բարի գալուստ Հայկական հերոսների թանգարան 🕊️\n\n"
            "Ընտրեք ստորև ներկայացված տարբերակներից՝ սկսելու համար։",
            reply_markup=kb,
        )
        return

    param = args[1].strip()
    decoded = unquote(param)

    match = re.search(r"[0-9a-f]{24}$", decoded)
    if not match:
        await message.answer(
            "🇦🇲 Բարի գալուստ Հայկական հերոսների թանգարան 🕊️\n\n"
            "Այս հղումը չի պարունակում հերոսի տվյալներ։",
            reply_markup=kb,
        )
        return

    hero_id = match.group(0)
    wait_msg = await message.answer("⏳ Սպասեք…")

    hero = await heroes_collection.find_one({"_id": ObjectId(hero_id)})
    if not hero:
        await wait_msg.edit_text("❌ Այդ հղումով հերոս չի գտնվել։")
        return

    # ✅ Better than loading all heroes docs:
    # Get only ids (still O(N) but much lighter than full docs)
    hero_ids = await heroes_collection.find({}, {"_id": 1}).to_list(length=None)
    all_ids = [str(h["_id"]) for h in hero_ids]
    total = len(all_ids)
    current_index = all_ids.index(hero_id) if hero_id in all_ids else 0

    cache_key = f"hero:{hero_id}"
    set_cached_hero(cache_key, all_ids)

    caption = fix_unclosed_tags(build_caption(hero, current_index, total))
    keyboard = build_keyboard("all", current_index, total, cache_key)

    img_path = None
    try:
        try:
            await wait_msg.delete()
        except Exception:
            pass

        img_url = hero.get("img_url")
        if img_url:
            img_path = await compose_hero_image(img_url)
            photo = types.FSInputFile(img_path)
            await message.answer_photo(
                photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.warning(f"⚠️ Failed to send composed image: {e}")
        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    finally:
        # clean temp file if compose_hero_image creates a temp local file
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass


@router.callback_query(F.data == "connect_info")
async def show_connect_info(cb: types.CallbackQuery):
    description = (
        "📢 Երբ դուք միացնեք ձեր ալիքը՝ բոտը շաբաթվա ընթացքում ավտոմատ կերպով կհրապարակի "
        "հայ հերոսների մասին հիշատակի գրառումներ ձեր ալիքում։\n\n"
        "⚙️ Բոտը կօգտագործի միայն ձեր թույլատրությունը հրապարակումներ կատարելու համար։\n\n"
        "Սեղմեք ներքևի կոճակը՝ ալիքը միացնելու համար։"
    )

    connect_button = KeyboardButton(
        text="📡 Կապել ալիք",
        request_chat=types.KeyboardButtonRequestChat(
            request_id=1,
            chat_is_channel=True,
            chat_is_created=True,
        ),
    )

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[connect_button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await cb.message.answer(description, reply_markup=reply_kb)
    await cb.answer()
