"""Telegram custom emoji IDs used by the bot.

All custom emoji IDs live in one place.  Message text is rendered with
``<tg-emoji>`` and keyboard buttons use ``icon_custom_emoji_id``.

If a custom emoji is animated in Telegram, it will animate automatically in
messages/clients that support it.  The bot does not need a separate animation
API call.
"""
from __future__ import annotations

CUSTOM_EMOJIS: dict[str, tuple[str, str]] = {
    # Original set
    "user": ("5258011929993026890", "👤"),
    "sword": ("5375560310096668561", "⚔️"),
    "strength": ("5158970452298696854", "💪"),
    "armenia_1": ("5071091435692886022", "🇦🇲"),
    "arm": ("5163411676116027081", "🦾"),
    "repeat": ("5172652336908076986", "🔁"),
    "badge": ("5377340123069296871", "🦾"),
    "check": ("5375530344109845665", "✅"),
    "cross": ("5375414568971414238", "✝️"),
    "armenia_2": ("5375312460418918893", "🇦🇲"),
    "armenia_3": ("5411455658186778270", "🇦🇲"),
    "armenia_4": ("5206194584085895608", "🇦🇲"),

    # Added set
    "search": ("6032850693348399258", "🔎"),
    "book": ("5404425896234884282", "📖"),
    "robot": ("5406683326750691396", "🤖"),
    "heart": ("5159110811829929374", "❤️"),
    "phone": ("5407025283456835913", "📱"),
    "church": ("5172492873362311131", "⛪️"),
    "statue": ("5172757988808590993", "🗽"),
    "lion": ("5163467751209043842", "🦁"),
    "candle": ("5350571717922167592", "🕯"),
    "star": ("5035122768216066110", "⭐️"),
}


def emoji_id(name: str) -> str:
    """Return only the Telegram custom emoji ID."""
    return CUSTOM_EMOJIS[name][0]
