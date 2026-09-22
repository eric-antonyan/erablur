from aiogram import Router, types, F
<<<<<<< HEAD
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    WebAppInfo,
)
from loguru import logger
from bson.regex import Regex
from app.db.mongo import heroes_collection, history_collection, users_collection
from app.db.redis_db import cache
from app.utils.cache import get_cached_hero, set_cached_hero
import re
import html
from app.db.mongo_stats import increment_user_search
=======
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from uuid import uuid4
import re
import html
import os
from app.db.database import db
from app.db.file_cache import cache
>>>>>>> 54c1deb (commit)
from app.utils.util import compose_hero_image

router = Router()

<<<<<<< HEAD
PAGE_SIZE = 1
=======
>>>>>>> 54c1deb (commit)
CB_PREFIX = "hero_page"
ARMENIAN_FLAG_URL = "https://upload.wikimedia.org/wikipedia/commons/2/2f/Flag_of_Armenia.svg"
MAX_CAPTION_LEN = 1024

<<<<<<< HEAD

# --- Clean and format text ---
def sanitize_html(text: str) -> str:
    """Remove all HTML tags and leave plain readable text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_duplicate_sentences(text: str) -> str:
    """Remove repeating sentences often duplicated in Zinapah."""
    sentences = re.split(r"[։\.]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    unique, seen = [], set()
    for s in sentences:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return "։ ".join(unique).strip() + "։"


def format_bio_text(bio: str) -> str:
    """Format biography text in patriotic Armenian tone."""
    bio = sanitize_html(bio)
    bio = re.sub(r"(?<=\D)(?=\d)", " ", bio)  # insert missing spaces before digits
    bio = re.sub(r"\s{2,}", " ", bio)
    bio = remove_duplicate_sentences(bio)

    paragraphs = re.split(r"[։\.]", bio)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    formatted = []
    for p in paragraphs:
        formatted.append(f"«{p}։»")

    return "\n\n".join(formatted[:10])


# --- Build caption ---
def build_caption(hero, index, total):
    bio = format_bio_text(hero.get("bio", ""))
    name = f"{hero['name']['first']} {hero['name']['last']}"
    birth = hero["date"].get("birth", "")
    death = hero["date"].get("dead", "")
=======
                          

def fix_html_tags(text: str) -> str:
    """Fix unclosed HTML tags in text."""
    if not text: return text
    tags = ['b', 'i', 'code', 'pre', 'u', 's', 'blockquote']
    for tag in tags:
        opens = text.count(f'<{tag}>')
        closes = text.count(f'</{tag}>')
        if opens > closes:
            text += f'</{tag}>' * (opens - closes)
    return text

def format_bio_text(bio: str) -> str:
    """Patriotic bio formatting with custom punctuation logic."""
    if not bio: return "Տվյալներ չկան"

                                            
    if "</p><p>" in bio:
        bio = bio.split("</p><p>")[0]

                                                      
    bio = bio.replace("<strong>", "<b>").replace("</strong>", "</b>՝\n")
    
                        
    bio = re.sub(r"<(br|br/|br\s/)>", "\n", bio, flags=re.IGNORECASE)
    bio = re.sub(r"</b>՝\s*\n+", "</b>՝\n", bio)                    
    bio = bio.replace("</p>", "\n\n")

                                       
    bio = re.sub(r"<(?!/?(b|i|u|s|code|blockquote)(?=>|\s))[^>]+>", "", bio)
    bio = html.unescape(bio)
    bio = re.sub(r"[ \t]+", " ", bio) 
    bio = re.sub(r"\n{3,}", "\n\n", bio)
    
    return fix_html_tags(bio).strip()

def build_caption(hero: dict, index: int, total: int) -> str:
    """Builds a high-quality caption with expandable bio."""
    bio_display = format_bio_text(hero.get("bio", ""))
    
                                                   
    if 'name' in hero and isinstance(hero['name'], dict):
        first_name = hero['name'].get('first', '')
        last_name = hero['name'].get('last', '')
        birth = hero.get('date', {}).get('birth', '')
        death = hero.get('date', {}).get('dead', '')
    else:
        first_name = hero.get('first_name', '')
        last_name = hero.get('last_name', '')
        birth = hero.get('birth_date', '')
        death = hero.get('death_date', '')

    name = f"{first_name} {last_name}".strip()
>>>>>>> 54c1deb (commit)
    region = hero.get("region", "")
    war = hero.get("war", "")

    caption = (
<<<<<<< HEAD
        f"֍ ՀԱՎԵՐԺ ՓԱՌՔ ֍\n"
        f"🇦🇲 <b>{name}</b> ֍ \n"
        f"📅 {birth} - {death}\n"
        f"📍 {region}\n"
        f"⚔️ {war}\n\n"
        f"🕯️ {bio}\n\n"
        f"֍ ՀԱՎԵՐԺ ՓԱՌՔ ֍\n\n"
        f"<i>{index + 1}/{total}</i>"
    )

    if len(caption) > MAX_CAPTION_LEN:
        cutoff = caption[: MAX_CAPTION_LEN - 3]
        cutoff = re.sub(r"<[^>]*$", "", cutoff)
        cutoff = re.sub(r"\s+\S*$", "", cutoff)
        caption = cutoff.strip() + "..."

    return caption


# --- Build inline keyboard ---
def build_keyboard(query, index, total, more_url):
    prev_i = (index - 1) % total
    next_i = (index + 1) % total

    buttons = [
        [
            InlineKeyboardButton(
                text="⬅️ Նախորդ",
                callback_data=f"{CB_PREFIX}|{query}|{prev_i}",
            ),
            InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton(
                text="Հաջորդ ➡️",
                callback_data=f"{CB_PREFIX}|{query}|{next_i}",
            ),
        ],
    ]

    # Optional web app button
    if more_url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Ավելին 🌐", web_app=WebAppInfo(url=more_url)
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Message handler (main search) ---
@router.message()
async def search_hero(message: types.Message):
    query = message.text.strip()
    logger.info(f"🔍 Searching hero for query: {query}")
    increment_user_search(message.from_user, query)
    print("r")

    # Split query into words for flexible searching
    parts = query.split()
    filt = {}

    if len(parts) >= 2:
        # Searching by both first + last name in any order
        first, last = parts[0], parts[1]
        filt = {
            "$or": [
                {"$and": [
                    {"name.first": Regex(first, "i")},
                    {"name.last": Regex(last, "i")},
                ]},
                {"$and": [
                    {"name.first": Regex(last, "i")},
                    {"name.last": Regex(first, "i")},
                ]},
            ]
        }
    else:
        # Single word → match first name or last name
        filt = {
            "$or": [
                {"name.first": Regex(query, "i")},
                {"name.last": Regex(query, "i")},
            ]
        }

    heroes = [h async for h in heroes_collection.find(filt)]
    total = len(heroes)

    if not heroes:
        await message.answer("❌ Հերոս չի գտնվել։ Փորձեք այլ անուն կամ ազգանուն։")
        return

    set_cached_hero(query, [str(h["_id"]) for h in heroes])
    hero = heroes[0]
    caption = build_caption(hero, 0, total)
    kb = build_keyboard(query, 0, total, hero.get("bio_link", ""))

    # --- 📜 Save search history (Redis + Mongo) ---
    user_id = str(message.from_user.id)
    query_text = query

    # Redis cache: keep last 10 searches
    cache.lpush(f"history:{user_id}", query_text)
    cache.ltrim(f"history:{user_id}", 0, 9)

    # MongoDB permanent log
    await history_collection.insert_one(
        {
            "user_id": user_id,
            "query": query_text,
            "hero_name": f"{hero['name']['first']} {hero['name']['last']}",
            "hero_id": str(hero["_id"]),
            "searched_at": message.date,
        }
    )

    cache.incr("stats:searches:total")
    cache.sadd("stats:users", user_id)
    cache.sadd("stats:heroes", hero["name"]["last"])
    await cache.set("stats:last_search_time", message.date.isoformat())

    img_path = await compose_hero_image(hero["img_url"])
    try:
        await message.answer_photo(
            types.FSInputFile(img_path),
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning(f"⚠️ Could not send photo ({hero.get('img_url')}): {e}")
        await message.answer_photo(
            ARMENIAN_FLAG_URL,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )

@router.callback_query(F.data.startswith(CB_PREFIX))
async def paginate_hero(cb: types.CallbackQuery):
    try:
        _, query, idx = cb.data.split("|")
        index = int(idx)
    except Exception as e:
        logger.warning(f"⚠️ Invalid callback data: {cb.data} ({e})")
        await cb.answer("Սխալ տվյալ։", show_alert=True)
        return

    
    parts = query.split()
    if len(parts) >= 2:
        first, last = parts[0], parts[1]
        filt = {
            "$or": [
                {"$and": [
                    {"name.first": Regex(first, "i")},
                    {"name.last": Regex(last, "i")},
                ]},
                {"$and": [
                    {"name.first": Regex(last, "i")},
                    {"name.last": Regex(first, "i")},
                ]},
            ]
        }
    else:
        filt = {
            "$or": [
                {"name.first": Regex(query, "i")},
                {"name.last": Regex(query, "i")},
            ]
        }

    heroes = [h async for h in heroes_collection.find(filt)]
    total = len(heroes)
    if not heroes:
        await cb.answer("Արդյունքներ չկան։", show_alert=True)
        return

    hero = heroes[index % total]
    caption = build_caption(hero, index, total)
    kb = build_keyboard(query, index, total, hero.get("bio_link", ""))

    try:
        img_path = await compose_hero_image(hero["img_url"])
        media = InputMediaPhoto(
            media=types.FSInputFile(img_path),
            caption=caption,
            parse_mode="HTML",
        )
        await cb.message.edit_media(media=media, reply_markup=kb)
    except Exception as e:
        logger.warning(f"⚠️ edit_media failed: {e}")
        try:
            flag_media = InputMediaPhoto(
                media=ARMENIAN_FLAG_URL, caption=caption, parse_mode="HTML"
            )
            await cb.message.edit_media(media=flag_media, reply_markup=kb)
        except Exception as e2:
            logger.warning(f"⚠️ even flag failed: {e2}")
            await cb.message.edit_caption(
                caption=caption, parse_mode="HTML", reply_markup=kb
            )

    await cb.answer()
=======
        "⚔️ <b>հավերժ փառք</b> ⚔️\n"
        f"<tg-emoji emoji-id='5375414568971414238'>✝️</tg-emoji> <b>{name}</b>\n"
        f"📅 {birth} - {death}\n"
        f"📍 {region}\n"
        f"⚔️ {war}\n\n"
        f"<blockquote expandable>🕯️ {bio_display}</blockquote>\n\n"
        f"<i>{index + 1}/{total}</i>\n\n"
        "<tg-emoji emoji-id=''></tg-emoji> <b>մեր հերոսները ապրում են մեր հիշողության մեջ</b>"
    )

    if len(caption) > MAX_CAPTION_LEN:
        caption = caption[:MAX_CAPTION_LEN-3] + "..."
    return caption

def build_keyboard(mode: str, index: int, total: int, key: str = None, more_url: str = None):
    prev_i = (index - 1) % total
    next_i = (index + 1) % total
    
    buttons = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"{CB_PREFIX}|{mode}|{key}|{prev_i}"),
            InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data=f"{CB_PREFIX}|{mode}|{key}|{next_i}"),
        ]
    ]
    
                                                 
    if more_url:
        buttons.append([InlineKeyboardButton(text="🌐 Ավելին", web_app=WebAppInfo(url=more_url))])

    buttons.append([InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="museum_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

                  

@router.message()
async def search_hero(message: types.Message):
    """Main text search handler."""
    query = message.text.strip()
    if query.startswith('/'): return

    await message.bot.send_chat_action(message.chat.id, "typing")
    
                                                                   
    heroes = db.get_heroes_by_name(query) if len(query.split()) == 1 else db.get_heroes_by_names(*query.split()[:2])
    
    if not heroes:
        await message.answer(
            f"❌ <b>Ցավում ենք, «{query}» անունով հերոս չի գտնվել</b>",
            parse_mode="HTML"
        )
        return

    total = len(heroes)
    cache_key = f"search:{uuid4().hex[:8]}"
    cache.set(cache_key, [h['id'] for h in heroes], ttl=3600)
    
    hero = heroes[0]
    caption = build_caption(hero, 0, total)
    kb = build_keyboard("search", 0, total, cache_key, hero.get("bio_link"))

    try:
        img_path = await compose_hero_image(hero.get("img_url", ""))
        await message.answer_photo(types.FSInputFile(img_path), caption=caption, parse_mode="HTML", reply_markup=kb)
        if os.path.exists(img_path): os.remove(img_path)
    except Exception:
        await message.answer_photo(ARMENIAN_FLAG_URL, caption=caption, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith(CB_PREFIX))
async def paginate_hero(cb: types.CallbackQuery):
    """Handles 'Next' and 'Previous' buttons for searches."""
    try:
        _, mode, key, idx = cb.data.split("|")
        index = int(idx)
        hero_ids = cache.get(key)
        if not hero_ids: return await cb.answer("⌛ Տվյալները ժամկետանց են", show_alert=True)
        
        total = len(hero_ids)
        hero = db.get_hero(hero_ids[index % total])
        caption = build_caption(hero, index, total)
        kb = build_keyboard(mode, index, total, key, hero.get("bio_link"))
        
        img_path = await compose_hero_image(hero.get("img_url", ""))
        media = InputMediaPhoto(media=types.FSInputFile(img_path) if os.path.exists(img_path) else ARMENIAN_FLAG_URL, 
                                caption=caption, parse_mode="HTML")
        await cb.message.edit_media(media=media, reply_markup=kb)
        if os.path.exists(img_path): os.remove(img_path)
    except Exception as e:
        logger.error(f"Pagination error: {e}")
        await cb.answer("Սխալ տվյալ:")

    await cb.answer()
>>>>>>> 54c1deb (commit)
