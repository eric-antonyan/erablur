"""Drop-in aiogram 3 helper for opening the Vercel Mini App as a real Telegram WebApp."""
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo


def webapp_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    url = webapp_url.strip().rstrip("/")
    if not url.startswith("https://"):
        raise ValueError("WEBAPP_URL must be an https:// URL")
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📱 Բացել հավելվածը",
                web_app=WebAppInfo(url=url),
            )
        ]]
    )


async def install_persistent_webapp_button(bot: Bot, webapp_url: str) -> None:
    url = webapp_url.strip().rstrip("/")
    if not url.startswith("https://"):
        raise ValueError("WEBAPP_URL must be an https:// URL")
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Բացել հավելվածը",
            web_app=WebAppInfo(url=url),
        )
    )
