"""Custom Telegram emoji + colored-button helpers.

The bot uses an outgoing client-session middleware, so existing handlers can
keep simple strings like ``"🔎 Որոնել"``.  Before a request is sent:

* supported native emoji are converted into Telegram custom emoji entities;
* unsupported UI emoji are removed instead of falling back to static emoji;
* inline/reply keyboard emoji become ``icon_custom_emoji_id`` icons;
* keyboard buttons receive Telegram's primary/success/danger styles.
"""
from __future__ import annotations

import re
from html import escape
from typing import Any

from app.config.custom_emojis import CUSTOM_EMOJIS, emoji_id


# Native emoji aliases that can be represented by the custom set supplied by
# the bot owner.  Only sensible aliases are mapped; unknown emoji are removed
# from bot UI text rather than shown as static emoji.
EMOJI_ALIASES: dict[str, str] = {
    # exact supplied fallbacks
    "🔎": "search",
    "📖": "book",
    "🤖": "robot",
    "❤️": "heart",
    "❤": "heart",
    "👤": "user",
    "📱": "phone",
    "🔁": "repeat",
    "⛪️": "church",
    "⛪": "church",
    "🗽": "statue",
    "🦾": "arm",
    "🦁": "lion",
    "🕯️": "candle",
    "🕯": "candle",
    "⭐️": "star",
    "⭐": "star",
    "⚔️": "sword",
    "⚔": "sword",
    "💪": "strength",
    "✅": "check",
    "✝️": "cross",
    "✝": "cross",
    "🇦🇲": "armenia_1",

    # close semantic aliases already used in the project
    "🔍": "search",
    "📚": "book",
    "📜": "book",
    "📄": "book",
    "📋": "book",
    "🧾": "book",
    "📝": "book",
    "🤖": "robot",
    "🧠": "robot",
    "💬": "robot",
    "👥": "user",
    "👨": "user",
    "📡": "phone",
    "📢": "phone",
    "📧": "phone",
    "📨": "phone",
    "🔄": "repeat",
    "♻️": "repeat",
    "♻": "repeat",
    "↩️": "repeat",
    "↩": "repeat",
    "⬅️": "repeat",
    "⬅": "repeat",
    "➡️": "repeat",
    "➡": "repeat",
    "⏭️": "repeat",
    "⏭": "repeat",
    "🏛️": "statue",
    "🏛": "statue",
    "🏅": "statue",
    "🏆": "statue",
    "🦸": "statue",
    "🕊️": "candle",
    "🕊": "candle",
    "💎": "star",
    "🔥": "strength",
    "⚙️": "arm",
    "⚙": "arm",
    "🧩": "arm",
    "💻": "arm",
    "💾": "arm",
    "➕": "check",
    "📥": "check",
    "📤": "check",
}

# Protect already-rendered custom emoji so middleware is idempotent.
_TG_EMOJI_RE = re.compile(r"<tg-emoji\b[^>]*>.*?</tg-emoji>", re.IGNORECASE | re.DOTALL)

# Broad UI-emoji matcher.  It intentionally includes common dingbats/arrows so
# unsupported static emoji don't leak into the bot UI.  Armenian text and HTML
# tags are unaffected.
_NATIVE_EMOJI_RE = re.compile(
    r"(?:"
    r"[\U0001F1E6-\U0001F1FF]{2}|"
    r"[\U0001F300-\U0001FAFF]|"
    r"[\u2300-\u23FF]|"
    r"[\u2600-\u27BF]"
    r")(?:\uFE0F)?(?:\u200D(?:[\U0001F300-\U0001FAFF]|[\u2600-\u27BF])(?:\uFE0F)?)*"
)

# Longer tokens first (e.g. flag / variation-selector sequences).
_ALIAS_TOKENS = tuple(sorted(EMOJI_ALIASES, key=len, reverse=True))


def custom_emoji(name: str, fallback: str | None = None) -> str:
    """Return a Telegram HTML ``tg-emoji`` entity."""
    custom_id, default_fallback = CUSTOM_EMOJIS[name]
    visible = fallback or default_fallback
    return f'<tg-emoji emoji-id="{custom_id}">{escape(visible)}</tg-emoji>'


def ce(name: str, fallback: str | None = None) -> str:
    """Short alias used in templates."""
    return custom_emoji(name, fallback)


def render_custom_emojis(text: str) -> str:
    """Convert native UI emoji in HTML text to custom emoji entities.

    Existing ``<tg-emoji>`` blocks are protected, making this safe to call on
    text that already uses :func:`ce`.
    """
    if not text:
        return text

    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"\x00TGE{len(protected) - 1}\x00"

    working = _TG_EMOJI_RE.sub(protect, text)

    generated: list[str] = []
    for token in _ALIAS_TOKENS:
        if token not in working:
            continue
        name = EMOJI_ALIASES[token]
        while token in working:
            marker = f"\x00CE{len(generated)}\x00"
            generated.append(custom_emoji(name, token))
            working = working.replace(token, marker, 1)

    # Anything still matching an emoji range has no supplied custom ID. Remove
    # it instead of leaving a non-custom/static emoji in the UI.
    working = _NATIVE_EMOJI_RE.sub("", working)
    working = re.sub(r"[ \t]{2,}", " ", working)

    for i, value in enumerate(generated):
        working = working.replace(f"\x00CE{i}\x00", value)
    for i, value in enumerate(protected):
        working = working.replace(f"\x00TGE{i}\x00", value)
    return working


def _strip_button_native_emoji(text: str) -> tuple[str, str | None]:
    """Return (plain_label, detected_custom_emoji_name)."""
    label = text or ""
    detected: str | None = None

    stripped = label.lstrip()
    for token in _ALIAS_TOKENS:
        if stripped.startswith(token):
            detected = EMOJI_ALIASES[token]
            stripped = stripped[len(token):].lstrip()
            break

    # Strip every remaining static/native emoji from labels. Telegram renders
    # the icon separately through icon_custom_emoji_id.
    stripped = _NATIVE_EMOJI_RE.sub("", stripped)
    stripped = re.sub(r"[ \t]{2,}", " ", stripped).strip()
    return stripped or "•", detected


def infer_button_style(button: Any) -> str | None:
    """Choose Telegram's built-in button color from button semantics."""
    callback = str(getattr(button, "callback_data", "") or "").lower()
    text = str(getattr(button, "text", "") or "").lower()
    hay = f"{callback} {text}"

    danger = ("delete", "disconnect", "cancel", "close", "clear", "remove", "ջնջ", "անջատ", "չեղարկ", "փակել", "մաքրել")
    success = ("support", "pay", "confirm", "connect", "add", "check", "աջակց", "վճար", "միացնել", "ավելացնել", "հաստատ")

    if any(key in hay for key in danger):
        return "danger"
    if any(key in hay for key in success):
        return "success"
    if callback == "noop":
        return None
    return "primary"


def infer_button_icon(button: Any, detected: str | None = None) -> str | None:
    """Infer a custom emoji icon when the label did not provide one."""
    if detected:
        return detected

    callback = str(getattr(button, "callback_data", "") or "").lower()
    text = str(getattr(button, "text", "") or "").lower()
    has_url = bool(getattr(button, "url", None) or getattr(button, "web_app", None))
    hay = f"{callback} {text}"

    rules: tuple[tuple[tuple[str, ...], str], ...] = (
        (("back", "return", "menu", "վերադառնալ", "գլխավոր"), "repeat"),
        (("search", "որոն"), "search"),
        (("ai_", "hay tseghakron", "ai ", "assistant", "վիկտորին"), "robot"),
        (("profile", "user", "օգտատեր"), "user"),
        (("support", "donat", "աջակց", "վճար"), "heart"),
        (("channel", "ալիք"), "phone"),
        (("museum", "hero", "հերոս", "թանգարան"), "statue"),
        (("star", "stars"), "star"),
        (("war", "պատերազմ"), "sword"),
        (("terms", "about", "history", "source", "կենսագր", "մասին", "պայման"), "book"),
        (("connect", "phone"), "phone"),
        (("confirm", "check", "ավելաց", "import", "export"), "check"),
    )
    for needles, name in rules:
        if any(needle in hay for needle in needles):
            return name
    if has_url:
        return "book"
    return None


def decorate_button(button: Any) -> Any:
    """Apply custom icon + color to an aiogram keyboard button in-place."""
    if not hasattr(button, "text"):
        return button

    plain_text, detected = _strip_button_native_emoji(str(button.text or ""))
    button.text = plain_text

    if not getattr(button, "icon_custom_emoji_id", None):
        name = infer_button_icon(button, detected)
        if name:
            button.icon_custom_emoji_id = emoji_id(name)

    if not getattr(button, "style", None):
        style = infer_button_style(button)
        if style:
            button.style = style
    return button


def decorate_markup(markup: Any) -> Any:
    """Decorate InlineKeyboardMarkup or ReplyKeyboardMarkup in-place."""
    rows = getattr(markup, "inline_keyboard", None)
    if rows is None:
        rows = getattr(markup, "keyboard", None)
    if rows is None:
        return markup

    for row in rows:
        for button in row:
            decorate_button(button)
    return markup
