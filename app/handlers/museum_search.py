from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bson import ObjectId, Regex
from loguru import logger
from urllib.parse import quote, unquote
from uuid import uuid4
import re, html

from app.db.mongo import heroes_collection
from app.utils.cache import get_cached_hero, set_cached_hero
from app.db.redis_db import cache

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
class MuseumState(StatesGroup):
    searching = State()


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

    cache_key = f"search:{uuid4().hex[:8]}"
    set_cached_hero(cache_key, [str(h["_id"]) for h in heroes])

    hero = heroes[0]
    caption = build_caption(hero, 0, total)
    kb = build_keyboard("search", 0, total, cache_key)
    await message.answer_photo(hero["img_url"], caption=caption, parse_mode="HTML", reply_markup=kb)
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
    await cb.message.answer_photo(hero["img_url"], caption=caption, parse_mode="HTML", reply_markup=kb)
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
        cache.set(key, w, ex=3600)
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
    await cb.message.answer_photo(hero["img_url"], caption=caption, parse_mode="HTML", reply_markup=kb)
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
        media = InputMediaPhoto(media=hero["img_url"], caption=caption, parse_mode="HTML")
        await cb.message.edit_media(media=media, reply_markup=kb)
    except Exception:
        await cb.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=kb)

    await cb.answer()
