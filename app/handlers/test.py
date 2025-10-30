from aiogram import Router, types

router = Router()

@router.message()
async def get_emoji_id(message: types.Message):
    EMOJI = {
        "heart": "5375517579467040395",
        "swords": "5375560310096668561",
        "recycle": "5373129839643469899",
    }

    # ❤️⚔️♻️ Premium emoji test
    msg = (
        f"<tg-emoji emoji-id='{EMOJI['heart']}'>❤️</tg-emoji> "
        f"<b>ՀԱՎԵՐԺ ՓԱՌՔ</b> "
        f"<tg-emoji emoji-id='{EMOJI['swords']}'>⚔️</tg-emoji>\n\n"
        f"<tg-emoji emoji-id='{EMOJI['recycle']}'>♻️</tg-emoji> Test premium emojis"
    )

    await message.answer(msg)
