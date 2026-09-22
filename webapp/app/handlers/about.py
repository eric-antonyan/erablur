from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

@router.callback_query(lambda c: c.data == "about")
async def about_page(cb: types.CallbackQuery):
    """Show 'About Us' section."""
    text = (
        "📜 <b>ՄԵՐ ՄԱՍԻՆ</b>\n\n"
        "🇦🇲 <b>Հայկական Հերոսների Թանգարան</b> — Telegram բոտ, "
        "որն ստեղծվել է՝ մեր հերոսների հիշատակը պահպանելու, "
        "նրանց կյանքի պատմությունները տարածելու և նոր սերունդներին ոգեշնչելու նպատակով։\n\n"
        "🧩 Բոլոր տվյալները և կենսագրությունները բոտը ստանում է "
        "պաշտոնական <b>Զինապահ (zinapah.am)</b> կայքից՝ "
        "հանրային հասանելի տվյալների հիման վրա։\n\n"
        "⚙️ Բոտը ստեղծվել է օգտագործելով <b>Python (Aiogram)</b>, "
        "<b>MongoDB</b> և <b>Redis</b>՝ արագ և ճշգրիտ աշխատանքի համար։\n\n"
        "👨‍💻 Ծրագրավորող՝ <b>Armat Soft</b>\n"
        "📧 Կապ՝ <i>@ArmatSupport</i>\n\n"
        "🕊️ Մեր հերոսների հիշատակը հավերժ է։"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="back_to_menu")]
    ])

    await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()
