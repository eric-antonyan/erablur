import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================= CONFIG =================
BOT_TOKEN = "8361057703:AAFh8bPfIH_vhfgMNhAKGPTI1uwcSazIpJ8"

# ================= SETUP =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
router = Router()

dp.include_router(router)

# ================= HANDLERS =================

@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        '<tg-emoji emoji-id="5348285966392007590">🇦🇲</tg-emoji>  <b>Bot is running!</b>\n'
        "🔥 Welcome!"
    )

@router.message(F.text)
async def echo_handler(message: Message):
    await message.answer(
        f"💬 You said: <code>{message.text}</code>"
    )

# ================= MAIN =================

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 Bot started...")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())