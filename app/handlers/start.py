<<<<<<< HEAD
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
=======
from __future__ import annotations

import re
from urllib.parse import unquote

from aiogram import F, Router, types
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.config.settings import settings
from app.db.database import db
from app.db.file_cache import cache
from app.handlers.museum_search import _send_hero
from app.utils.custom_emoji import ce

router = Router(name="start")


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = []
    if settings.webapp_url.startswith("https://"):
        rows.append([InlineKeyboardButton(text="📱 Բացել հավելվածը", web_app=WebAppInfo(url=settings.webapp_url))])
    rows.extend([
        [
            InlineKeyboardButton(text="🏛️ Թանգարան", callback_data="museum"),
            InlineKeyboardButton(text="🔎 Որոնել հերոս", switch_inline_query_current_chat=""),
        ],
        [
            InlineKeyboardButton(text="🤖 Hay Tseghakron", callback_data="ai_menu"),
            InlineKeyboardButton(text="👤 Իմ պրոֆիլը", callback_data="profile"),
        ],
    ])
    if settings.support_enabled:
        rows.append([
            InlineKeyboardButton(text="❤️ Աջակցել", callback_data="support_home"),
            InlineKeyboardButton(text="📜 Մեր մասին", callback_data="about"),
        ])
    else:
        rows.append([InlineKeyboardButton(text="📜 Մեր մասին", callback_data="about")])
    rows.append([InlineKeyboardButton(text="📡 Իմ ալիքները", callback_data="manage_channels")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_main_menu(message: types.Message, *, edit: bool = False) -> None:
    text = (
        f"{ce('sword')} <b>Բարի գալուստ «Հայոց Հերոսներ»</b>\n\n"
        "Սա հայ հերոսների հիշատակը պահպանող թվային թանգարանն է, որտեղ կարող եք "
        "բացահայտել նրանց կյանքը, սխրանքներն ու պատմությունները։\n\n"
        "🔎 Որոնեք հերոսին անունով\n"
        "📖 Կարդացեք կենսագրություններն ու կարևոր փաստերը\n"
        "🤖 Հարցեր տվեք Hay Tseghakron օգնականին\n"
        + ("❤️ Աջակցեք նախագծի պահպանմանն ու զարգացմանը\n\n" if settings.support_enabled else "\n")
        + f"{ce('armenia_1')} <b>Հիշում ենք։ Պատմում ենք։ Հավերժացնում ենք։</b>"
    )
    if edit:
        try:
            await message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
            return
        except Exception:
            pass
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


async def open_manage_panel_logic(event: types.Message | types.CallbackQuery) -> None:
    user_id = str(event.from_user.id)
    channels = db.get_user_channels(user_id)
    rows: list[list[InlineKeyboardButton]] = []
    if channels:
        text = "📡 <b>Ձեր միացված ալիքները</b>\n\nԸնտրեք ալիքը՝ կառավարելու համար։"
        for channel in channels:
            channel_id = channel.get("channel_id") or channel.get("id")
            title = str(channel.get("title") or "Անանուն ալիք")
            rows.append([InlineKeyboardButton(text=f"📢 {title}"[:60], callback_data=f"channel_manage|show|{channel_id}")])
    else:
        text = (
            "📡 <b>Դուք դեռ ալիք չեք միացրել</b>\n\n"
            "Միացրեք ալիքը, որպեսզի բոտը կարողանա ամենօրյա հիշատակի գրառումներ հրապարակել։"
        )
    rows.extend([
        [InlineKeyboardButton(text="➕ Միացնել նոր ալիք", callback_data="connect_info")],
        [InlineKeyboardButton(text="↩️ Գլխավոր մենյու", callback_data="back_to_menu")],
    ])
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            await event.message.answer(text, parse_mode="HTML", reply_markup=markup)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=markup)


@router.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject | None = None, type: str = "answer") -> None:
    user = message.from_user
    db.save_user(
        str(user.id),
        user.username or "",
        user.first_name or "",
        user.last_name or "",
    )
    param = command.args if command and hasattr(command, "args") else None
    if param == "connect":
        await open_manage_panel_logic(message)
        return
    if not param:
        await show_main_menu(message, edit=type == "edit")
        return

    decoded = unquote(param)
    match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{24}", decoded)
    if not match:
        await show_main_menu(message)
        return

    hero_id = match.group(0)
    hero = db.get_hero(hero_id)
    if not hero:
        await message.answer("❌ Հերոսը չի գտնվել։", reply_markup=main_menu_keyboard())
        return
    heroes = db.get_all_heroes()
    ids = [str(item["id"]) for item in heroes]
    try:
        index = ids.index(str(hero_id))
    except ValueError:
        ids = [str(hero_id)]
        index = 0
    cache_key = f"hero_start:{hero_id}"
    cache.set(cache_key, ids, ttl=3600)
    await _send_hero(message, hero, index, len(ids), "all", cache_key)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data == "manage_channels")
async def handle_manage_callback(callback: types.CallbackQuery) -> None:
    await open_manage_panel_logic(callback)


@router.callback_query(F.data == "connect_info")
async def show_connect_info(callback: types.CallbackQuery) -> None:
    description = (
        "📢 Բոտը կարող է ամեն օր հիշատակի գրառում հրապարակել ձեր ալիքում։\n\n"
        "1. Նախ ավելացրեք բոտը ալիքում որպես ադմինիստրատոր։\n"
        "2. Սեղմեք ներքևի կոճակը և ընտրեք ալիքը։"
    )
    connect_button = KeyboardButton(
        text="📡 Ընտրել ալիք",
        request_chat=types.KeyboardButtonRequestChat(
            request_id=1,
            chat_is_channel=True,
        ),
    )
    await callback.message.answer(
        description,
        reply_markup=ReplyKeyboardMarkup(keyboard=[[connect_button]], resize_keyboard=True, one_time_keyboard=True),
    )
    await callback.answer()
>>>>>>> 54c1deb (commit)
