from aiogram import Router, types
from bson.regex import Regex
from app.db.mongo import heroes_collection, history_collection
import re, html

router = Router()
MAX_INLINE_RESULTS = 50


# ---------------------
# 🔹 Helpers
# ---------------------
def sanitize_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_caption(hero):
    name = f"{hero['name']['first']} {hero['name']['last']}"
    war = hero.get("war", "")
    region = hero.get("region", "")
    bio = sanitize_html(hero.get("bio", ""))
    bio_short = bio[:350] + "..." if len(bio) > 350 else bio
    return (
        f"֍ ՀԱՎԵՐԺ ՓԱՌՔ ֍\n"
        f"🇦🇲 <b>{name}</b>\n"
        f"⚔️ {war}\n"
        f"📍 {region}\n\n"
        f"🕯️ {bio_short}"
    )


# ---------------------
# 🔹 Inline search handler
# ---------------------
@router.inline_query()
async def inline_search(query: types.InlineQuery):
    text = query.query.strip()
    text = text.replace("և", "եվ")
    if not text:
        await query.answer([], switch_pm_text="Գրիր հերոսի անունը", switch_pm_parameter="start")
        return

    # Split user query into parts
    parts = text.split(maxsplit=1)
    regex_text = re.escape(text)  # escape spaces and regex chars

    # Build flexible Mongo filter
    conditions = [
        {"name.first": Regex(text, "i")},
        {"name.last": Regex(text, "i")},
        {"$expr": {"$regexMatch": {
            "input": {"$concat": ["$name.first", " ", "$name.last"]},
            "regex": regex_text,
            "options": "i"
        }}}
    ]

    if len(parts) == 2:
        first, last = parts
        conditions.append({
            "$and": [
                {"name.first": Regex(first, "i")},
                {"name.last": Regex(last, "i")}
            ]
        })
        conditions.append({
            "$and": [
                {"name.first": Regex(last, "i")},
                {"name.last": Regex(first, "i")}
            ]
        })

    query_filter = {"$or": conditions}

    heroes = [h async for h in heroes_collection.find(query_filter).limit(MAX_INLINE_RESULTS)]

    if not heroes:
        await query.answer([], switch_pm_text="Հերոս չի գտնվել", switch_pm_parameter="notfound")
        return

    results = []
    for hero in heroes:
        hero_id = str(hero["_id"])
        title = f"{hero['name']['first']} {hero['name']['last']}"
        description = hero.get("war", "Հայ հերոս")
        photo = hero.get("img_url") or "https://upload.wikimedia.org/wikipedia/commons/2/2f/Flag_of_Armenia.svg"
        caption = make_caption(hero)

        result = types.InlineQueryResultArticle(
            id=hero_id,
            title=title,
            description=description,
            thumbnail_url=photo,
            input_message_content=types.InputTextMessageContent(
                message_text=caption,
                parse_mode="HTML",
            ),
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🏛️ Դիտել թանգարանում", url=f"https://t.me/erablurbot?start={hero["_id"]}")]
            ])
        )
        results.append(result)

    await query.answer(results, cache_time=5, is_personal=True)


