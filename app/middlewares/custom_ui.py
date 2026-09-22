"""Outgoing Telegram UI middleware.

It upgrades existing handlers automatically, so every keyboard gets Telegram
custom-emoji icons and native button colors without rewriting 100+ button
constructors across the project.
"""
from __future__ import annotations

from typing import Any

from app.utils.custom_emoji import decorate_markup, render_custom_emojis


def _html_enabled(value: Any) -> bool:
    """True unless parse_mode was explicitly disabled with None.

    aiogram's Default('parse_mode') object is intentionally treated as enabled,
    because this project configures the Bot default parse mode as HTML.
    """
    return value is not None


def _decorate_nested(value: Any) -> Any:
    """Decorate mutable outgoing input objects (media/inline content/results)."""
    if value is None:
        return value

    if isinstance(value, (list, tuple)):
        for item in value:
            _decorate_nested(item)
        return value

    # Keyboard markup objects.
    if hasattr(value, "inline_keyboard") or hasattr(value, "keyboard"):
        return decorate_markup(value)

    # InputTextMessageContent / InputMedia* / similar mutable Telegram input
    # objects. Only transform text that is actually parsed as HTML.
    parse_mode = getattr(value, "parse_mode", object())
    html_ok = parse_mode is not None
    for attr in ("message_text", "caption"):
        current = getattr(value, attr, None)
        if html_ok and isinstance(current, str):
            try:
                setattr(value, attr, render_custom_emojis(current))
            except Exception:
                pass

    # Inline-query results can contain nested content and reply markups.
    for attr in ("reply_markup", "input_message_content", "media"):
        nested = getattr(value, attr, None)
        if nested is not None:
            _decorate_nested(nested)
    return value


async def custom_ui_middleware(make_request: Any, bot: Any, method: Any) -> Any:
    """aiogram client-session middleware for custom emoji + button styling."""
    updates: dict[str, Any] = {}

    parse_mode = getattr(method, "parse_mode", object())
    html_ok = _html_enabled(parse_mode)

    if html_ok:
        for attr in ("text", "caption"):
            current = getattr(method, attr, None)
            if isinstance(current, str):
                updates[attr] = render_custom_emojis(current)

    reply_markup = getattr(method, "reply_markup", None)
    if reply_markup is not None:
        updates["reply_markup"] = decorate_markup(reply_markup)

    # Handle captions in InputMedia and inline-mode InputTextMessageContent.
    for attr in ("media", "results"):
        nested = getattr(method, attr, None)
        if nested is not None:
            _decorate_nested(nested)
            updates[attr] = nested

    if updates:
        method = method.model_copy(update=updates)

    return await make_request(bot, method)
