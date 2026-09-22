<<<<<<< HEAD
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bson import ObjectId, Regex
from loguru import logger
from urllib.parse import quote, unquote
from uuid import uuid4
import re, html
from datetime import datetime, timezone
import os
from app.db.mongo import heroes_collection, history_collection
from app.utils.cache import get_cached_hero, set_cached_hero
from app.db.redis_db import cache
from app.db.mongo_stats import increment_user_search
from app.utils.util import compose_hero_image

router = Router()

CB_PREFIX = "museum_page"
ARMENIAN_FLAG_URL = "https://upload.wikimedia.org/wikipedia/commons/2/2f/Flag_of_Armenia.svg"
MAX_CAPTION_LEN = 1024


# ---------------------
# 🔹 TEXT UTILITIES
# ---------------------
def sanitize_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_duplicate_sentences(text: str) -> str:
    sentences = re.split(r"[։\.]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    unique, seen = [], set()
    for s in sentences:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return "։ ".join(unique).strip() + "։"


def format_bio_text(bio: str) -> str:
    bio = sanitize_html(bio)
    bio = re.sub(r"(?<=\D)(?=\d)", " ", bio)
    bio = re.sub(r"\s{2,}", " ", bio)
    bio = remove_duplicate_sentences(bio)
    paragraphs = re.split(r"[։\.]", bio)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    formatted = [f"«{p}։»" for p in paragraphs]
    return "\n\n".join(formatted[:10])


# ---------------------
# 🔹 SAFE CALLBACK BUILDER
# ---------------------
def make_callback(*parts, max_len=60):
    """Safely build callback_data string for Telegram (<=64 bytes)."""
    data = "|".join(parts)
    if len(data) > max_len:
        data = data[:max_len - 3] + "..."
    return data


# ---------------------
# 🔹 BUILD CAPTION + KEYBOARD
# ---------------------
def build_caption(hero, index, total):
    bio = format_bio_text(hero.get("bio", ""))
    name = f"{hero['name']['first']} {hero['name']['last']}"
    birth = hero["date"].get("birth", "")
    death = hero["date"].get("dead", "")
    region = hero.get("region", "")
    war = hero.get("war", "")

    caption = (
        f"֍ ՀԱՎԵՐԺ ՓԱՌՔ ֍\n"
        f"🇦🇲 <b>{name}</b>\n"
        f"📅 {birth} - {death}\n"
        f"📍 {region}\n"
        f"⚔️ {war}\n\n"
        f"🕯️ {bio}\n\n"
        f"<i>{index + 1}/{total}</i>"
    )

    if len(caption) > MAX_CAPTION_LEN:
        cutoff = caption[:MAX_CAPTION_LEN - 3]
        cutoff = re.sub(r"<[^>]*$", "", cutoff)
        caption = cutoff.strip() + "..."
    return caption


def build_keyboard(mode, index, total, key=None):
    prev_i = (index - 1) % total
    next_i = (index + 1) % total
    safe_key = quote(key or "_")

    buttons = [
        [
            InlineKeyboardButton(
                text="⬅️ Նախորդ",
                callback_data=make_callback(CB_PREFIX, mode, safe_key, str(prev_i))
            ),
            InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton(
                text="Հաջորդ ➡️",
                callback_data=make_callback(CB_PREFIX, mode, safe_key, str(next_i))
            ),
        ],
        [InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="museum_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------------
# 🔹 FSM STATE
# ---------------------
=======
from __future__ import annotations

import html
import re
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from loguru import logger

from app.db.database import db
from app.db.file_cache import cache
from app.utils.util import compose_hero_image, remove_temp_file

router = Router(name="museum")
CB_PREFIX = "museum_page"
MAX_CAPTION_LEN = 1024

# Store short ID -> actual cache key mapping
_pagination_cache = {}

def _store_cache_key(actual_key: str) -> str:
    """Store the actual cache key and return a short ID."""
    short_id = uuid4().hex[:6]  # 6 chars is enough
    _pagination_cache[short_id] = actual_key
    return short_id

def _get_cache_key(short_id: str) -> str | None:
    """Retrieve the actual cache key from short ID."""
    return _pagination_cache.pop(short_id, None)


def _plain_bio(value: str) -> str:
    text = str(value or "")
    # The source often contains a duplicated second <p> block.
    marker = "</p><p>"
    if marker in text:
        first, rest = text.split(marker, 1)
        if first.strip() and len(rest) > len(first) * 0.8:
            text = first
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or "Տվյալներ չկան"


def build_caption(hero: dict, index: int, total: int) -> str:
    name = html.escape(f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip() or "Անանուն հերոս")
    birth = html.escape(str(hero.get("birth_date") or "—"))
    death = html.escape(str(hero.get("death_date") or "—"))
    region = html.escape(str(hero.get("region") or "—"))
    war = html.escape(str(hero.get("war") or "—"))

    header = (
        "🇦🇲 <b>ՀԱՎԵՐԺ ՓԱՌՔ</b>\n"
        f"🕯️ <b>{name}</b>\n"
        f"📅 {birth} — {death}\n"
        f"📍 {region}\n"
        f"⚔️ {war}\n\n"
    )
    footer = f"\n\n<i>{index + 1}/{max(total, 1)}</i>"
    bio = html.escape(_plain_bio(hero.get("bio", "")))
    wrapper_len = len("<blockquote expandable>🕯️ </blockquote>")
    available = max(80, MAX_CAPTION_LEN - len(header) - len(footer) - wrapper_len - 8)
    if len(bio) > available:
        bio = bio[:available].rsplit(" ", 1)[0] + "…"
    return f"{header}<blockquote expandable>🕯️ {bio}</blockquote>{footer}"


def build_keyboard(
    mode: str,
    index: int,
    total: int,
    key: str | None = None,
    hero_id: str | None = None,
    more_url: str | None = None,
) -> InlineKeyboardMarkup:
    total = max(total, 1)
    prev_i = (index - 1) % total
    next_i = (index + 1) % total
    
    # Store the cache key and get a short ID
    short_id = _store_cache_key(key) if key else "noop"
    
    rows = [[
        InlineKeyboardButton(text="⬅️", callback_data=f"{CB_PREFIX}|{mode}|{short_id}|{prev_i}"),
        InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="noop"),
        InlineKeyboardButton(text="➡️", callback_data=f"{CB_PREFIX}|{mode}|{short_id}|{next_i}"),
    ]]
    if hero_id:
        rows.append([InlineKeyboardButton(text="🤖 Hay Tseghakron ամփոփում", callback_data=f"ai_explain|{hero_id}")])
    if more_url and str(more_url).startswith(("http://", "https://")):
        rows.append([InlineKeyboardButton(text="🌐 Սկզբնաղբյուր", url=str(more_url))])
    rows.append([InlineKeyboardButton(text="↩️ Թանգարան", callback_data="museum_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


>>>>>>> 54c1deb (commit)
class MuseumState(StatesGroup):
    searching = State()


<<<<<<< HEAD
# ---------------------
# 🔹 MUSEUM MENU
# ---------------------
@router.callback_query(lambda c: c.data in ["museum", "museum_menu"])
async def museum_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "🏛️ <b>Հայկական Հերոսների Թանգարան</b>\n\n"
        "🕊️ Սա մեր հերոսների հիշատակի սրբավայրն է։\n\n"
        "Ընտրեք բաժինը👇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕯️ Հիշում ենք...", callback_data="museum_search")],
        [
            InlineKeyboardButton(text="🏅 Բոլորը", callback_data="museum_all"),
            InlineKeyboardButton(text="⚔️ Մարտեր", callback_data="museum_wars"),
        ],
        [InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="back_to_menu")],
    ])
    await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


# ---------------------
# 🔹 SEARCH MODE
# ---------------------
@router.callback_query(lambda c: c.data == "museum_search")
async def museum_search_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer(
        "🕯️ Գրեք հերոսի անունը կամ ազգանունը՝ որոնելու համար թանգարանում։\n\n"
        "Օրինակ՝ <b>Ռոբերտ</b> կամ <b>Ռոբերտ Աբաջյան</b>",
        parse_mode="HTML",
    )
    await state.set_state(MuseumState.searching)
    await cb.answer()


@router.message(MuseumState.searching)
async def museum_searching(message: types.Message, state: FSMContext):
    query = re.sub(r"\s+", " ", message.text.strip())
    if not query:
        await message.answer("❌ Մուտքագրեք անուն կամ ազգանուն։")
        return

    parts = query.split()
    if len(parts) >= 2:
        first, last = parts[0], parts[1]
        filt = {"$or": [
            {"$and": [{"name.first": Regex(first, "i")}, {"name.last": Regex(last, "i")}]},
            {"$and": [{"name.first": Regex(last, "i")}, {"name.last": Regex(first, "i")}]},
        ]}
    else:
        filt = {"$or": [{"name.first": Regex(query, "i")}, {"name.last": Regex(query, "i")}]}

    heroes = [h async for h in heroes_collection.find(filt)]
    total = len(heroes)
    if not heroes:
        await message.answer("❌ Հերոս չի գտնվել։ Փորձեք այլ անուն։")
        return
    
    increment_user_search(message.from_user, query)

    cache_key = f"search:{uuid4().hex[:8]}"
    set_cached_hero(cache_key, [str(h["_id"]) for h in heroes])

    hero = heroes[0]
    caption = build_caption(hero, 0, total)
    kb = build_keyboard("search", 0, total, cache_key)
    img_path = await compose_hero_image(hero["img_url"])
    image = await message.answer_photo(hero["img_url"], caption=caption, parse_mode="HTML", reply_markup=kb)
    print("Exists:", os.path.exists(img_path))
    print("Path:", img_path)
    media = InputMediaPhoto(
        media=types.FSInputFile(img_path),
        caption=caption,
        parse_mode="HTML"
    )
    await image.edit_media(media, reply_markup=kb)
    await history_collection.insert_one({
        "user_id": str(message.from_user.id),
        "username": message.from_user.username,
        "query": query,
        "hero_id": str(hero["_id"]),
        "hero_name": f"{hero['name']['first']} {hero['name']['last']}",
        "searched_at": message.date.isoformat()
    })
    cache.set("stats:last_search_time", datetime.now(timezone.utc).isoformat())
    await state.clear()


# ---------------------
# 🔹 SHOW ALL HEROES
# ---------------------
@router.callback_query(lambda c: c.data == "museum_all")
async def show_all_heroes(cb: types.CallbackQuery):
    heroes = [h async for h in heroes_collection.find()]
    total = len(heroes)
    if not heroes:
        await cb.message.answer("❌ Թանգարանում դեռ հերոսներ չկան։")
        return

    cache_key = f"all:{uuid4().hex[:8]}"
    set_cached_hero(cache_key, [str(h["_id"]) for h in heroes])

    hero = heroes[0]
    caption = build_caption(hero, 0, total)
    kb = build_keyboard("all", 0, total, cache_key)
    img_path = await compose_hero_image(hero["img_url"])
    image = await cb.message.answer_photo(hero["img_url"], caption=caption, parse_mode="HTML", reply_markup=kb)
    media = InputMediaPhoto(
        media=types.FSInputFile(img_path),
        caption=caption,
        parse_mode="HTML"
    )
    await image.edit_media(media, reply_markup=kb)
    await cb.answer()


# ---------------------
# 🔹 SHOW WARS LIST
# ---------------------
@router.callback_query(lambda c: c.data == "museum_wars")
async def show_wars_list(cb: types.CallbackQuery):
    wars = await heroes_collection.distinct("war")
    wars = [w for w in wars if w]
    if not wars:
        await cb.message.answer("❌ Դեռևս պատերազմներ չկան տվյալների բազայում։")
        return

    keyboard = []
    for w in wars:
        key = f"war:{uuid4().hex[:8]}"
        await cache.set(key, w, ex=3600)
        keyboard.append([InlineKeyboardButton(text=f"⚔️ {w}", callback_data=make_callback("museum_war", key))])

    keyboard.append([InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="museum_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await cb.message.answer("⚔️ Ընտրեք պատերազմը՝ ցուցակը դիտելու համար։", reply_markup=kb)
    await cb.answer()


# ---------------------
# 🔹 FILTER HEROES BY WAR
# ---------------------
@router.callback_query(lambda c: c.data.startswith("museum_war|"))
async def filter_by_war(cb: types.CallbackQuery):
    try:
        _, cache_key = cb.data.split("|", 1)
        war = cache.get(cache_key)
    except Exception as e:
        logger.warning(f"Bad war key: {e}")
        await cb.answer("⛔ Ժամկետանց հղում։", show_alert=True)
        return

    if not war:
        await cb.answer("⛔ Ժամկետանց հղում։", show_alert=True)
        return

    heroes = [h async for h in heroes_collection.find({"war": war})]
    total = len(heroes)
    if not heroes:
        await cb.message.answer(f"❌ {war} բաժնում հերոսներ չկան։")
        return

    cache_key2 = f"warlist:{uuid4().hex[:8]}"
    set_cached_hero(cache_key2, [str(h["_id"]) for h in heroes])

    hero = heroes[0]
    caption = build_caption(hero, 0, total)
    kb = build_keyboard("war", 0, total, cache_key2)
    img_path = await compose_hero_image(hero["img_url"])
    image = await cb.message.answer_photo(hero["img_url"], caption=caption, parse_mode="HTML", reply_markup=kb)
    media = InputMediaPhoto(
        media=types.FSInputFile(img_path),
        caption=caption,
        parse_mode="HTML"
    )
    await image.edit_media(media, reply_markup=kb)
    await cb.answer()


# ---------------------
# 🔹 PAGINATION
# ---------------------
@router.callback_query(F.data.startswith(CB_PREFIX))
async def paginate_museum(cb: types.CallbackQuery):
    try:
        _, mode, key, idx = cb.data.split("|", 3)
        index = int(idx)
        key = unquote(key)
    except Exception as e:
        logger.warning(f"⚠️ Invalid callback: {cb.data} ({e})")
        await cb.answer("Սխալ տվյալ։", show_alert=True)
        return

    ids = get_cached_hero(key)
    if not ids:
        await cb.answer("⚠️ Տվյալներ չկան կամ ժամկետանց են։", show_alert=True)
        return

    total = len(ids)
    hero = await heroes_collection.find_one({"_id": ObjectId(ids[index % total])})
    caption = build_caption(hero, index, total)
    kb = build_keyboard(mode, index, total, key)

    try:
        img_path = await compose_hero_image(hero["img_url"])
        media = InputMediaPhoto(media=hero["img_url"], caption=caption, parse_mode="HTML")
        media = InputMediaPhoto(
            media=types.FSInputFile(img_path),
            caption=caption,
            parse_mode="HTML"
        )
        await cb.message.edit_media(media=media, reply_markup=kb)
    except Exception:
        await cb.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=kb)

    await cb.answer()
=======
@router.callback_query(F.data.in_({"museum", "museum_menu"}))
async def museum_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = (
        "🇦🇲 <b>Հայոց Հերոսներ</b>\n\n"
        "🕊️ Սա մեր հերոսների հիշատակի թվային թանգարանն է։\n\n"
        "Ընտրեք բաժինը։"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Որոնել անունով", callback_data="museum_search")],
        [
            InlineKeyboardButton(text="🏅 Բոլոր հերոսները", callback_data="museum_all"),
            InlineKeyboardButton(text="⚔️ Ըստ պատերազմի", callback_data="museum_wars"),
        ],
        [InlineKeyboardButton(text="🤖 Hay Tseghakron", callback_data="ai_menu")],
        [InlineKeyboardButton(text="↩️ Գլխավոր մենյու", callback_data="back_to_menu")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "museum_search")
async def museum_search_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "🔎 <b>Գրեք հերոսի անունը կամ ազգանունը</b>\n\n"
        "Օրինակ՝ <b>Ռոբերտ</b> կամ <b>Ռոբերտ Աբաջյան</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Չեղարկել", callback_data="museum_menu")]
        ]),
    )
    await state.set_state(MuseumState.searching)
    await callback.answer()


@router.message(MuseumState.searching)
async def museum_searching(message: types.Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Մուտքագրեք անուն կամ ազգանուն։")
        return
    if len(query) > 100:
        await message.answer("Որոնման տեքստը չափազանց երկար է։")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    heroes = db.get_heroes_by_name(query, limit=50)
    if not heroes:
        await state.clear()
        await message.answer(
            f"❌ «{html.escape(query)}» հարցմամբ հերոս չի գտնվել։\n\n"
            "Փորձեք անուն, ազգանուն կամ լրիվ անուն։",
            parse_mode="HTML",
        )
        return

    await state.clear()
    cache_key = f"search:{uuid4().hex[:10]}"
    cache.set(cache_key, [hero["id"] for hero in heroes], ttl=3600)
    hero = heroes[0]
    db.add_search_history(str(message.from_user.id), query, hero["id"], f"{hero['first_name']} {hero['last_name']}")
    db.increment_search_count(str(message.from_user.id), query)
    cache.set("stats:last_search_time", __import__("datetime").datetime.now().isoformat(timespec="seconds"), ttl=86400)
    await _send_hero(message, hero, 0, len(heroes), "search", cache_key)


@router.callback_query(F.data == "museum_all")
async def show_all_heroes(callback: types.CallbackQuery) -> None:
    heroes = db.get_all_heroes()
    if not heroes:
        await callback.answer("Թանգարանում դեռ գրառումներ չկան։", show_alert=True)
        return
    cache_key = f"all:{uuid4().hex[:10]}"
    cache.set(cache_key, [hero["id"] for hero in heroes], ttl=3600)
    await _send_hero(callback.message, heroes[0], 0, len(heroes), "all", cache_key)
    await callback.answer()


@router.callback_query(F.data == "museum_wars")
async def show_wars_list(callback: types.CallbackQuery) -> None:
    wars = db.get_all_wars()
    if not wars:
        await callback.answer("Պատերազմների ցանկը դատարկ է։", show_alert=True)
        return
    rows = []
    for war in wars[:90]:
        # Use shorter key for war selection
        short_key = f"w_{uuid4().hex[:6]}"
        cache.set(short_key, war, ttl=3600)
        rows.append([InlineKeyboardButton(text=f"⚔️ {war}"[:60], callback_data=f"museum_war|{short_key}")])
    rows.append([InlineKeyboardButton(text="↩️ Թանգարան", callback_data="museum_menu")])
    await callback.message.answer(
        "⚔️ <b>Ընտրեք պատերազմը կամ գործողությունը</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("museum_war|"))
async def filter_by_war(callback: types.CallbackQuery) -> None:
    cache_key = callback.data.split("|", 1)[1]
    war = cache.get(cache_key)
    if not war:
        await callback.answer("Հղման ժամկետը սպառվել է։", show_alert=True)
        return
    heroes = db.get_heroes_by_war(str(war))
    if not heroes:
        await callback.answer("Այս բաժնում հերոսներ չկան։", show_alert=True)
        return
    list_key = f"warlist:{uuid4().hex[:10]}"
    cache.set(list_key, [hero["id"] for hero in heroes], ttl=3600)
    await _send_hero(callback.message, heroes[0], 0, len(heroes), "war", list_key)
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PREFIX + "|"))
async def paginate_museum(callback: types.CallbackQuery) -> None:
    try:
        _, mode, short_id, raw_index = callback.data.split("|", 3)
        index = int(raw_index)
    except (ValueError, IndexError):
        await callback.answer("Սխալ տվյալ։", show_alert=True)
        return

    # Get the actual cache key from the short ID
    key = _get_cache_key(short_id)
    if not key:
        await callback.answer("Տվյալների ժամկետը սպառվել է։", show_alert=True)
        return

    hero_ids = cache.get(key)
    if not isinstance(hero_ids, list) or not hero_ids:
        await callback.answer("Տվյալների ժամկետը սպառվել է։", show_alert=True)
        return
    index %= len(hero_ids)
    hero = db.get_hero(str(hero_ids[index]))
    if not hero:
        await callback.answer("Հերոսը չի գտնվել։", show_alert=True)
        return

    caption = build_caption(hero, index, len(hero_ids))
    keyboard = build_keyboard(mode, index, len(hero_ids), key, hero["id"], hero.get("bio_link"))
    image_path = None
    try:
        image_path = await compose_hero_image(hero.get("img_url", ""))
        media = InputMediaPhoto(media=types.FSInputFile(image_path), caption=caption, parse_mode="HTML")
        await callback.message.edit_media(media=media, reply_markup=keyboard)
    except Exception as exc:
        logger.warning("Hero pagination image error: {}", exc)
        try:
            await callback.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)
    finally:
        remove_temp_file(image_path)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery) -> None:
    await callback.answer()


async def _send_hero(
    message: types.Message,
    hero: dict,
    index: int,
    total: int,
    mode: str,
    cache_key: str,
) -> None:
    caption = build_caption(hero, index, total)
    keyboard = build_keyboard(mode, index, total, cache_key, hero.get("id"), hero.get("bio_link"))
    image_path = None
    try:
        image_path = await compose_hero_image(hero.get("img_url", ""))
        await message.answer_photo(
            types.FSInputFile(image_path),
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as exc:
        logger.warning("Hero image send error: {}", exc)
        await message.answer(caption, parse_mode="HTML", reply_markup=keyboard)
    finally:
        remove_temp_file(image_path)
>>>>>>> 54c1deb (commit)
