"""Aiogram 3 callback handler for Broadcast popup buttons.

Include this Router in the same Python bot that opens the Mini App.
It uses the same MongoDB database as the Mini App API.
"""
import os
from aiogram import F, Router
from aiogram.types import CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

router = Router(name="hayoc_broadcast_callbacks")
_client = None


def _db():
    global _client
    if _client is None:
        uri = os.environ["MONGODB_URL"]
        _client = AsyncIOMotorClient(uri)
    return _client[os.getenv("MONGODB_DB_NAME", "erablur")]


@router.callback_query(F.data.startswith("hhpopup:"))
async def broadcast_popup(callback: CallbackQuery):
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Invalid action", show_alert=True)
        return
    campaign_id, index_raw = parts[1], parts[2]
    if campaign_id == "test":
        await callback.answer("Popup buttons are fully resolved after the broadcast is saved.", show_alert=True)
        return
    try:
        index = int(index_raw)
        campaign = await _db().broadcasts.find_one({"_id": ObjectId(campaign_id)})
        buttons = campaign.get("buttons", []) if campaign else []
        text = str(buttons[index].get("popup_text", "")) if 0 <= index < len(buttons) else ""
        await callback.answer(text or "Done", show_alert=True)
    except Exception:
        await callback.answer("This popup is unavailable.", show_alert=True)
