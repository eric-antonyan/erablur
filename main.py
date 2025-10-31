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
