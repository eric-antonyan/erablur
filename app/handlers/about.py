<<<<<<< HEAD
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
=======
from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.custom_emoji import ce

router = Router(name="about")


@router.callback_query(F.data == "about")
async def about_page(callback: types.CallbackQuery) -> None:
    text = (
        f"{ce('armenia_2')} <b>Հայոց Հերոսներ</b>\n\n"
        "Այս բոտի նպատակն է պահպանել և հասանելի դարձնել զոհված հայ զինծառայողների "
        "կենսագրական պատմությունները՝ հարգալից և որոնելի թվային ձևաչափով։\n\n"
        "📚 <b>Տվյալների աղբյուր</b>\n"
        "Հերոսների հիմնական գրառումները ներմուծված են Zinapah.am կայքից։ Յուրաքանչյուր գրառման մեջ "
        "հնարավորության դեպքում պահպանվում է սկզբնաղբյուրի հղումը։\n\n"
        "🤖 <b>Hay Tseghakron</b>\n"
        "AI օգնականը աշխատում է բոտի տեղական տվյալներով և հրահանգված է չհորինել բացակայող փաստեր։ "
        "AI պատասխանը կարող է սխալվել, ուստի կարևոր տվյալները ստուգեք սկզբնաղբյուրում։\n\n"
        "🔐 <b>Գաղտնիություն</b>\n"
        "Պահվում են Telegram օգտատիրոջ հիմնական պրոֆիլային տվյալները, որոնումների պատմությունը և օգտագործման վիճակագրությունը՝ "
        "բոտի աշխատանքի համար։\n\n"
        "👨‍💻 Մշակող՝ <b>Hay Tseghakron Team</b>\n"
        "📨 Կապ՝ @mahaparthay, @azatamartik, @kaputopel"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Բացել Zinapah.am", url="https://www.zinapah.am")],
        [InlineKeyboardButton(text="🤖 Hay Tseghakron", callback_data="ai_menu")],
        [InlineKeyboardButton(text="↩️ Գլխավոր մենյու", callback_data="back_to_menu")],
    ])
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
>>>>>>> 54c1deb (commit)
