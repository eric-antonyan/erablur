from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.db.redis_db import cache
from app.db.mongo import users_collection, history_collection
from app.utils.util import format_armenian_datetime

router = Router()


# --- 🧩 Helper: Get user info ---
async def get_user_data(user_id: str):
    """Get user info from Redis, fallback to Mongo."""
    user_id = str(user_id)
    user = cache.hgetall(f"user:{user_id}")
    if not user:
        user = await users_collection.find_one({"id": user_id}) or {}
    return user


# --- 🧩 Helper: Get user search history ---
async def get_user_history(user_id: str):
    """Get last 10 searches from Redis, fallback to Mongo."""
    user_id = str(user_id)
    history = cache.lrange(f"history:{user_id}", 0, 9)
    if not history:
        cursor = (
            history_collection.find({"user_id": user_id})
            .sort("searched_at", -1)
            .limit(10)
        )
        history = [doc.get("query", "—") async for doc in cursor]
    return history


# --- 🧩 Helper: Get global statistics ---
async def get_stats():
    """Fetch bot statistics from Redis (fallback-safe)."""
    total_users = cache.scard("stats:users") or 0
    unique_search_users = cache.scard("stats:users") or 0
    total_searches = int(cache.get("stats:searches:total") or 0)
    unique_heroes = cache.scard("stats:heroes") or 0
    last_search = cache.get("stats:last_search_time") or "Չկա"

    return {
        "total_users": total_users,
        "unique_search_users": unique_search_users,
        "total_searches": total_searches,
        "unique_heroes": unique_heroes,
        "last_search": last_search,
    }


# --- 📈 Profile command (User stats & history) ---
@router.callback_query(lambda c: c.data == "profile")
async def show_profile(cb: types.CallbackQuery):
    user_id = str(cb.from_user.id)

    # Load user data & stats
    user = await get_user_data(user_id)
    history = await get_user_history(user_id)
    stats = await get_stats()

    # --- Compose Profile Message ---
    text = (
        f"👤 <b>{user.get('first_name', cb.from_user.first_name)} {user.get('last_name', cb.from_user.last_name or '')}</b>\n"
        f"📱 @{user.get('username', cb.from_user.username or 'չկա')}\n"
        f"🆔 {user.get('id', user_id)}\n\n"
        f"📊 <b>Վիճակագրություն</b>:\n"
        f"🔍 Ընդհանուր որոնումներ՝ <b>{stats['total_searches']}</b>\n"
        f"🕰️ Վերջին որոնումը՝ <b>{format_armenian_datetime(stats['last_search'])}</b>\n\n"
    )

    if history:
        text += "🕯️ <b>Ձեր վերջին որոնումները</b>:\n"
        print(history)
        for i, q in enumerate(history, 1):
            text += f"{i}. {q}\n"
    else:
        text += "🕯️ Պատմություն դեռ չկա։\n"

    # --- Buttons ---
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Մաքրել պատմությունը", callback_data="clear_history")],
        [InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="back_to_menu")]
    ])

    await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


# --- 🧹 Clear user search history ---
@router.callback_query(lambda c: c.data == "clear_history")
async def clear_history(cb: types.CallbackQuery):
    user_id = str(cb.from_user.id)
    cache.delete(f"history:{user_id}")
    await history_collection.delete_many({"user_id": user_id})
    await cb.message.answer("✅ Ձեր որոնումների պատմությունը մաքրվեց։")
    await cb.answer()


# --- ↩️ Return to Main Menu ---
@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(cb: types.CallbackQuery):
    from app.handlers.start import start_cmd
    await start_cmd(cb.message)
    await cb.answer()
