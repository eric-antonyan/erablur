from aiogram import Bot, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from random import choice
from loguru import logger
from bson import ObjectId
from app.db.mongo import heroes_collection, channels_collection
from app.handlers.museum_search import build_caption

# ---------------------
# ⚙️ SCHEDULER CONFIG
# ---------------------
scheduler = AsyncIOScheduler()
CB_PREFIX = "daily_post"
BOT_USERNAME = "armenian_heroes_bot"  # 🧩 replace with your bot username


# ---------------------
# 🔹 DAILY HERO POST FUNCTION
# ---------------------
async def send_daily_hero(bot: Bot):
    """
    Pick one random hero from MongoDB and send
    their info to all connected channels.
    Also checks channel access and cleans invalid ones.
    """
    # --- Get heroes ---
    heroes = [h async for h in heroes_collection.find()]
    if not heroes:
        logger.warning("⚠️ No heroes found in database.")
        return

    hero = choice(heroes)
    caption = build_caption(hero, 0, 1)

    # --- Add footer ---
    footer = (
        "\n\n───────────────\n"
        "📢 Ցանկանու՞մ եք, որ բոտը նաև ձեր ալիքում հրապարակումներ անի?\n"
        "Սեղմեք ներքևի կոճակը👇"
    )
    caption_with_footer = f"{caption}{footer}"

    # --- Inline button (link to bot) ---
    inline_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📡 Միացնել իմ ալիքը",
                    url=f"https://t.me/{BOT_USERNAME}?start=connect",
                )
            ]
        ]
    )

    # --- Get connected channels ---
    channels = [ch async for ch in channels_collection.find()]
    if not channels:
        logger.info("ℹ️ No connected channels yet.")
        return

    logger.info(
        f"📢 Sending daily hero: {hero['name']['first']} {hero['name']['last']} "
        f"to {len(channels)} channels."
    )

    # --- Send hero to each channel ---
    for ch in channels:
        channel_id = ch.get("channel_id")
        title = ch.get("title", "Unknown")

        try:
            # ✅ Check if bot can access the channel
            chat = await bot.get_chat(channel_id)

            if not chat or chat.type != "channel":
                raise Exception("Invalid chat type or inaccessible channel.")

            # ✅ Send hero
            await bot.send_photo(
                chat_id=channel_id,
                photo=hero["img_url"],
                caption=caption_with_footer,
                parse_mode="HTML",
                reply_markup=inline_kb,
            )
            logger.info(f"✅ Sent hero to {title} ({channel_id})")

        except Exception as e:
            # --- Remove invalid channels ---
            if "chat not found" in str(e).lower() or "forbidden" in str(e).lower():
                await channels_collection.delete_one({"channel_id": channel_id})
                logger.warning(f"🧹 Removed invalid channel: {title} ({channel_id})")
            else:
                logger.error(f"❌ Failed to send to {title} ({channel_id}): {e}")


# ---------------------
# 🔹 SCHEDULER SETUP
# ---------------------
def setup_daily_scheduler(bot: Bot):
    """
    Create and start APScheduler for daily hero posting.
    Runs once every day at a fixed hour.
    """
    scheduler.add_job(
        send_daily_hero,
        trigger="cron",
        hour=10,  # ⏰ change time here (server time)
        minute=0,
        args=[bot],
    )
    scheduler.start()
    logger.info("🕒 Daily hero scheduler started — runs every day at 10:00.")
