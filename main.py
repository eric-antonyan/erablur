<<<<<<< HEAD
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from app.config.settings import BOT_TOKEN, TEST_BOT_TOKEN
from app.handlers import start, inline_search, profile, about, museum_search, channel_manage, admin
from loguru import logger


async def main():
    logger.info("Starting Armenian Heroes Museum Bot 🇦🇲")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(about.router)
    dp.include_router(museum_search.router)
    dp.include_router(channel_manage.router)
    dp.include_router(inline_search.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
=======
from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from loguru import logger

from app.config.settings import settings
from app.db.database import db
from app.handlers import about, admin, ai_assistant, channel_manage, inline_search, museum_search, profile, start, support
from app.middlewares.custom_ui import custom_ui_middleware
from app.scheduler import setup_daily_scheduler, stop_scheduler
from app.services.cryptomus import cryptomus
from app.services.deepseek import deepseek
from app.services.payment_webhook import payment_webhook


async def configure_bot(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Գլխավոր մենյու"),
        BotCommand(command="ai", description="Hay Tseghakron օգնական"),
        BotCommand(command="support", description="Աջակցել նախագծին"),
        BotCommand(command="paysupport", description="Վճարման օգնություն"),
        BotCommand(command="terms", description="Աջակցության պայմաններ"),
        BotCommand(command="admin", description="Ադմին վահանակ"),
    ])
    if settings.webapp_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Բացել հավելվածը", web_app=WebAppInfo(url=settings.webapp_url))
        )


async def main() -> None:
    settings.validate()
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level, enqueue=True, backtrace=False, diagnose=False)
    logger.add("logs/bot.log", level=settings.log_level, rotation="10 MB", retention="14 days", compression="zip", enqueue=True)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    # Upgrade every outgoing message/keyboard with custom emoji icons and
    # Telegram primary/success/danger button styles.
    bot.session.middleware(custom_ui_middleware)
    dispatcher = Dispatcher()
    # Specific FSM/callback routers before the large admin router.
    dispatcher.include_router(start.router)
    dispatcher.include_router(museum_search.router)
    dispatcher.include_router(ai_assistant.router)
    dispatcher.include_router(support.router)
    dispatcher.include_router(profile.router)
    dispatcher.include_router(about.router)
    dispatcher.include_router(channel_manage.router)
    dispatcher.include_router(inline_search.router)
    dispatcher.include_router(admin.router)

    try:
        await configure_bot(bot)
        setup_daily_scheduler(bot)
        await payment_webhook.start(bot)
        me = await bot.get_me()
        logger.info("Bot started as @{} | DB={} | DeepSeek={} | model={}", me.username, type(db).__name__, deepseek.configured, settings.deepseek_model)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        stop_scheduler()
        await payment_webhook.stop()
        await cryptomus.close()
        await deepseek.close()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
>>>>>>> 54c1deb (commit)
