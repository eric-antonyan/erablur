import os
from app.db.mongo_stats import get_global_stats, users_collection
from aiogram import types, F, Router

ADMIN_ID = int(os.getenv("OWNER_ID"))

router = Router()

@router.message(F.text == "/admin")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    total_users, total_searches, last_user = await get_global_stats()

    text = (
        f"🇦🇲 <b>Հայկական Հերոսների Թանգարան — Վարչական Տվյալներ</b>\n\n"
        f"👥 Օգտատերերի քանակ՝ <b>{total_users}</b>\n"
        f"🔎 Ընդհանուր որոնումներ՝ <b>{total_searches}</b>\n"
    )

    if last_user:
        updated_at = last_user.get("updated_at")
        updated_at_str = updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else "—"
        print(last_user)

        text += (
            f"🕰 Վերջին ակտիվ օգտագործող՝ {"@" + last_user["username"] if last_user["username"] else last_user["id"]}\n"
            f"📱 Վերջին որոնումը՝ <code>{last_user.get('last_query', '—')}</code>\n"
            f"📅 Թարմացվել է՝ {updated_at_str}\n"
        )

    top_users = users_collection.find().sort("search_count", -1).limit(5)
    top = [u async for u in top_users]
    if top:
        text += "\n🏆 <b>Ամենաակտիվ հայրենասերներ</b>\n"
        for i, u in enumerate(top, start=1):
            print(u)
            if "search_count" in u and u["search_count"] > 0:
                text += f"{i}. {"@" + last_user["username"] if last_user["username"] else last_user["id"]} — {u.get('search_count', 0)} որոնում\n"

    await message.answer(text, parse_mode="HTML")
