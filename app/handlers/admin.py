<<<<<<< HEAD
import os
from app.db.mongo_stats import get_global_stats, users_collection
from aiogram import types, F, Router

ADMIN_ID = int(os.getenv("OWNER_ID"))

router = Router()

@router.message(F.text == "/admin")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    total_users, total_searches, last_user = await get_global_stats()

    text = (
        f"🇦🇲 <b>Հայկական Հերոսների Թանգարան — Վարչական Տվյալներ</b>\n\n"
        f"👥 Օգտատերերի քանակ՝ <b>{total_users}</b>\n"
        f"🔎 Ընդհանուր որոնումներ՝ <b>{total_searches}</b>\n"
    )

    if last_user:
        updated_at = last_user.get("updated_at")
        updated_at_str = updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else "—"
        print(last_user)

        text += (
            f"🕰 Վերջին ակտիվ օգտագործող՝ {"@" + last_user["username"] if last_user["username"] else last_user["id"]}\n"
            f"📱 Վերջին որոնումը՝ <code>{last_user.get('last_query', '—')}</code>\n"
            f"📅 Թարմացվել է՝ {updated_at_str}\n"
        )

    top_users = users_collection.find().sort("search_count", -1).limit(5)
    top = [u async for u in top_users]
    if top:
        text += "\n🏆 <b>Ամենաակտիվ հայրենասերներ</b>\n"
        for i, u in enumerate(top, start=1):
            print(u)
            if "search_count" in u and u["search_count"] > 0:
                text += f"{i}. {"@" + last_user["username"] if last_user["username"] else last_user["id"]} — {u.get('search_count', 0)} որոնում\n"

    await message.answer(text, parse_mode="HTML")
=======
from __future__ import annotations

import asyncio
import html
import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config.settings import settings
from app.db.database import db
from app.db.file_cache import cache

router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_user_search = State()
    waiting_hero_search = State()
    waiting_add_hero_json = State()
    waiting_edit_hero_json = State()
    waiting_import_json = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def _deny(event: types.Message | types.CallbackQuery) -> bool:
    if is_admin(event.from_user.id):
        return False
    if isinstance(event, types.CallbackQuery):
        await event.answer("Մուտքն արգելված է։", show_alert=True)
    else:
        await event.answer("⛔ Դուք չունեք ադմինիստրատորի իրավունք։")
    return True


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Վիճակագրություն", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Օգտատերեր", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="🦸 Հերոսներ", callback_data="admin_heroes"),
            InlineKeyboardButton(text="📡 Ալիքներ", callback_data="admin_channels"),
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🤖 AI վիճակ", callback_data="admin_ai"),
        ],
        [
            InlineKeyboardButton(text="❤️ Աջակցություն", callback_data="admin_support"),
            InlineKeyboardButton(text="💾 Backup / Export", callback_data="admin_backup"),
        ],
        [InlineKeyboardButton(text="🧹 Մաքրել cache", callback_data="admin_clear_cache")],
        [InlineKeyboardButton(text="❌ Փակել", callback_data="close_admin")],
    ])


async def _show_admin(message: types.Message, *, edit: bool = False) -> None:
    text = "🔐 <b>Ադմինիստրատորի վահանակ</b>\n\nԸնտրեք գործողությունը։"
    if edit:
        try:
            await message.edit_text(text, parse_mode="HTML", reply_markup=admin_keyboard())
            return
        except Exception:
            pass
    await message.answer(text, parse_mode="HTML", reply_markup=admin_keyboard())


@router.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    await state.clear()
    await _show_admin(message)


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.clear()
    await _show_admin(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data == "close_admin")
async def close_admin(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.clear()
    await callback.message.edit_text("Ադմին վահանակը փակվեց։")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    stats, ai_stats, channels, donation_stats = await asyncio.gather(
        asyncio.to_thread(db.get_global_stats),
        asyncio.to_thread(db.get_ai_global_stats),
        asyncio.to_thread(db.get_all_channels),
        asyncio.to_thread(db.get_donation_stats),
    )
    heroes = await asyncio.to_thread(db.get_all_heroes)
    with_bio = sum(bool(hero.get("bio")) for hero in heroes)
    with_image = sum(bool(hero.get("img_url")) for hero in heroes)
    text = (
        "📊 <b>Համակարգի վիճակագրություն</b>\n\n"
        f"👥 Օգտատերեր՝ <b>{stats['total_users']}</b>\n"
        f"🔎 Որոնումներ՝ <b>{stats['total_searches']}</b>\n"
        f"🦸 Հերոսներ՝ <b>{stats['total_heroes']}</b>\n"
        f"📝 Կենսագրությամբ՝ <b>{with_bio}</b>\n"
        f"🖼️ Նկարով՝ <b>{with_image}</b>\n"
        f"📡 Ալիքներ՝ <b>{len(channels)}</b>\n"
        f"🤖 AI հարցումներ՝ <b>{ai_stats['requests']}</b>\n"
        f"🧮 AI tokens՝ <b>{ai_stats['prompt_tokens'] + ai_stats['completion_tokens']}</b>\n"
        f"❤️ Հաստատված աջակցություններ՝ <b>{donation_stats['paid_orders']}</b>\n"
        f"⭐ Stars՝ <b>{donation_stats['stars_total']:.0f}</b>\n"
        f"💎 Crypto invoice՝ <b>${donation_stats['crypto_total']:.2f}</b>"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    stats = await asyncio.to_thread(db.get_global_stats)
    text = f"👥 <b>Օգտատերեր՝ {stats['total_users']}</b>\n\n🏆 <b>Ամենաակտիվները</b>\n"
    for index, user in enumerate(stats.get("top_users", []), 1):
        identity = f"@{user['username']}" if user.get("username") else str(user.get("id"))
        text += f"{index}. {html.escape(identity)} — {int(user.get('search_count') or 0)} որոնում\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Որոնել օգտատեր", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_search_user")
async def admin_search_user(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.set_state(AdminStates.waiting_user_search)
    await callback.message.answer("Գրեք Telegram user ID-ն կամ @username-ը։")
    await callback.answer()


@router.message(AdminStates.waiting_user_search)
async def admin_user_result(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    query = (message.text or "").strip()
    user = db.get_user(query) if query.isdigit() else db.get_user_by_username(query)
    await state.clear()
    if not user:
        await message.answer("Օգտատերը չի գտնվել։", reply_markup=admin_keyboard())
        return
    history = db.get_user_history(str(user["id"]), 10)
    text = (
        "👤 <b>Օգտատիրոջ տվյալներ</b>\n\n"
        f"ID՝ <code>{html.escape(str(user['id']))}</code>\n"
        f"Անուն՝ {html.escape(str(user.get('first_name') or '—'))} {html.escape(str(user.get('last_name') or ''))}\n"
        f"Username՝ @{html.escape(str(user.get('username') or 'չկա'))}\n"
        f"Որոնումներ՝ <b>{int(user.get('search_count') or 0)}</b>\n"
        f"Միացել է՝ {html.escape(str(user.get('joined_at') or '—'))}\n\n"
        "<b>Վերջին որոնումները</b>\n"
    )
    text += "\n".join(f"• {html.escape(str(item.get('query') or '—'))}" for item in history) or "—"
    await message.answer(text, parse_mode="HTML", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_heroes")
async def admin_heroes(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    count = await asyncio.to_thread(db.count_heroes)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Որոնել / խմբագրել", callback_data="admin_search_hero")],
        [InlineKeyboardButton(text="➕ Ավելացնել JSON-ով", callback_data="admin_add_hero")],
        [InlineKeyboardButton(text="📥 Import JSON ֆայլ", callback_data="admin_import_json")],
        [InlineKeyboardButton(text="📤 Export JSON", callback_data="admin_export_json")],
        [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")],
    ])
    await callback.message.edit_text(f"🦸 <b>Հերոսների կառավարում</b>\n\nԸնդհանուր՝ <b>{count}</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_search_hero")
async def admin_search_hero(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.set_state(AdminStates.waiting_hero_search)
    await callback.message.answer("Գրեք հերոսի անունը, ազգանունը կամ ID-ն։")
    await callback.answer()


@router.message(AdminStates.waiting_hero_search)
async def admin_hero_results(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    query = (message.text or "").strip()
    hero = db.get_hero(query)
    heroes = [hero] if hero else db.get_heroes_by_name(query, 10)
    await state.clear()
    if not heroes:
        await message.answer("Հերոսը չի գտնվել։", reply_markup=admin_keyboard())
        return
    rows = []
    for item in heroes:
        name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
        rows.append([InlineKeyboardButton(text=name[:58], callback_data=f"admin_hero|{item['id']}")])
    rows.append([InlineKeyboardButton(text="↩️ Ադմին", callback_data="admin_back")])
    await message.answer("Ընտրեք գրառումը։", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("admin_hero|"))
async def admin_hero_detail(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    hero_id = callback.data.split("|", 1)[1]
    hero = db.get_hero(hero_id)
    if not hero:
        await callback.answer("Հերոսը չի գտնվել։", show_alert=True)
        return
    name = f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()
    bio = _plain_text(hero.get("bio", ""))
    if len(bio) > 700:
        bio = bio[:697] + "…"
    text = (
        f"🦸 <b>{html.escape(name)}</b>\n"
        f"ID՝ <code>{html.escape(hero_id)}</code>\n"
        f"Ծնունդ՝ {html.escape(str(hero.get('birth_date') or '—'))}\n"
        f"Մահ՝ {html.escape(str(hero.get('death_date') or '—'))}\n"
        f"Մարզ՝ {html.escape(str(hero.get('region') or '—'))}\n"
        f"Գործողություն՝ {html.escape(str(hero.get('war') or '—'))}\n\n"
        f"{html.escape(bio or 'Կենսագրություն չկա։')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Խմբագրել JSON-ով", callback_data=f"admin_edit_hero|{hero_id}")],
        [InlineKeyboardButton(text="🗑️ Ջնջել", callback_data=f"admin_delete_hero|{hero_id}")],
        [InlineKeyboardButton(text="↩️ Հերոսներ", callback_data="admin_heroes")],
    ])
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_add_hero")
async def admin_add_hero(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.set_state(AdminStates.waiting_add_hero_json)
    await callback.message.answer(
        "Ուղարկեք մեկ JSON օբյեկտ։ Պարտադիր դաշտեր՝ first_name, last_name։\n\n"
        '<code>{"first_name":"Արամ","last_name":"Օրինակյան","birth_date":"","death_date":"","region":"","war":"","img_url":"","bio_link":"","bio":""}</code>',
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_add_hero_json)
async def admin_add_hero_save(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    try:
        payload = json.loads(message.text or "")
        if not isinstance(payload, dict):
            raise ValueError("JSON must be an object")
        if not str(payload.get("first_name") or "").strip() or not str(payload.get("last_name") or "").strip():
            raise ValueError("first_name and last_name are required")
        hero_id = str(payload.get("id") or uuid4())
        db.save_hero(hero_id, payload)
    except (json.JSONDecodeError, ValueError) as exc:
        await message.answer(f"JSON սխալ՝ {html.escape(str(exc))}", parse_mode="HTML")
        return
    await state.clear()
    await message.answer(f"✅ Հերոսն ավելացվեց։\nID՝ <code>{hero_id}</code>", parse_mode="HTML", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("admin_edit_hero|"))
async def admin_edit_hero(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    hero_id = callback.data.split("|", 1)[1]
    hero = db.get_hero(hero_id)
    if not hero:
        await callback.answer("Հերոսը չի գտնվել։", show_alert=True)
        return
    await state.update_data(edit_hero_id=hero_id)
    await state.set_state(AdminStates.waiting_edit_hero_json)
    editable = {key: hero.get(key, "") for key in (
        "first_name", "last_name", "birth_date", "death_date", "region", "war", "img_url", "bio_link", "bio"
    )}
    preview = json.dumps(editable, ensure_ascii=False, indent=2)
    await callback.message.answer(
        "Ուղարկեք ամբողջական կամ մասնակի JSON՝ դաշտերը թարմացնելու համար։\n\n"
        f"<pre>{html.escape(preview[:3200])}</pre>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_edit_hero_json)
async def admin_edit_hero_save(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    data = await state.get_data()
    hero_id = str(data.get("edit_hero_id") or "")
    hero = db.get_hero(hero_id)
    if not hero:
        await state.clear()
        await message.answer("Հերոսը չի գտնվել։")
        return
    try:
        patch = json.loads(message.text or "")
        if not isinstance(patch, dict):
            raise ValueError("JSON must be an object")
        allowed = {"first_name", "last_name", "birth_date", "death_date", "region", "war", "img_url", "bio_link", "bio"}
        hero.update({key: value for key, value in patch.items() if key in allowed})
        db.save_hero(hero_id, hero)
    except (json.JSONDecodeError, ValueError) as exc:
        await message.answer(f"JSON սխալ՝ {html.escape(str(exc))}", parse_mode="HTML")
        return
    await state.clear()
    cache.delete(f"hero:{hero_id}")
    await message.answer("✅ Գրառումը թարմացվեց։", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("admin_delete_hero|"))
async def admin_delete_hero_confirm(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    hero_id = callback.data.split("|", 1)[1]
    await callback.message.answer(
        "⚠️ Վստա՞հ եք, որ ցանկանում եք ջնջել գրառումը։",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Այո, ջնջել", callback_data=f"admin_delete_confirm|{hero_id}")],
            [InlineKeyboardButton(text="❌ Չեղարկել", callback_data="admin_heroes")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_confirm|"))
async def admin_delete_hero(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    hero_id = callback.data.split("|", 1)[1]
    deleted = db.delete_hero(hero_id)
    cache.delete(f"hero:{hero_id}")
    await callback.message.edit_text(
        "✅ Գրառումը ջնջվեց։" if deleted else "Գրառումը արդեն չկար։",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Հերոսներ", callback_data="admin_heroes")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_import_json")
async def admin_import_json(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.set_state(AdminStates.waiting_import_json)
    await callback.message.answer("Ուղարկեք UTF-8 JSON ֆայլ՝ հերոսների array-ով։")
    await callback.answer()


@router.message(AdminStates.waiting_import_json, F.document)
async def admin_import_json_file(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    document = message.document
    if not document.file_name or not document.file_name.lower().endswith(".json"):
        await message.answer("Ուղարկեք .json ֆայլ։")
        return
    if document.file_size and document.file_size > 25 * 1024 * 1024:
        await message.answer("Ֆայլը չափազանց մեծ է (առավելագույնը 25 MB)։")
        return
    file = await message.bot.download(document)
    try:
        payload = json.loads(file.read().decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Root JSON value must be an array")
        imported = 0
        failed = 0
        for item in payload:
            try:
                if not isinstance(item, dict):
                    raise ValueError
                hero_id = str(item.get("id") or uuid4())
                db.save_hero(hero_id, item)
                imported += 1
            except Exception:
                failed += 1
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        await message.answer(f"Import սխալ՝ {html.escape(str(exc))}", parse_mode="HTML")
        return
    await state.clear()
    await message.answer(f"✅ Import ավարտվեց։ Հաջող՝ {imported}, սխալ՝ {failed}։", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_export_json")
async def admin_export_json(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    heroes = await asyncio.to_thread(db.get_all_heroes)
    export_dir = Path("temp")
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"heroes_export_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(heroes, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        await callback.message.answer_document(types.FSInputFile(path), caption=f"Հերոսներ՝ {len(heroes)}")
    finally:
        path.unlink(missing_ok=True)
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.answer("Ուղարկեք հաղորդագրությունը։ Այն copy կանվի բոլոր գրանցված օգտատերերին։")
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext) -> None:
    if await _deny(message):
        return
    users = await asyncio.to_thread(db.get_all_users)
    progress = await message.answer(f"Broadcast սկսվեց՝ {len(users)} օգտատեր։")
    sent = 0
    failed = 0
    for index, user in enumerate(users, 1):
        try:
            await message.bot.copy_message(
                chat_id=int(user["id"]),
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            sent += 1
        except Exception:
            failed += 1
        if index % 25 == 0:
            await asyncio.sleep(1)
    await state.clear()
    await progress.edit_text(f"✅ Broadcast ավարտվեց։ Ուղարկված՝ {sent}, սխալ՝ {failed}։")


@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    channels = await asyncio.to_thread(db.get_all_channels)
    text = f"📡 <b>Կապված ալիքներ՝ {len(channels)}</b>\n\n"
    for channel in channels[:80]:
        text += f"• {html.escape(str(channel.get('title') or 'Անանուն'))} — <code>{channel.get('channel_id')}</code>\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text[:3900], parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_ai")
async def admin_ai(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    stats = await asyncio.to_thread(db.get_ai_global_stats)
    text = (
        "🤖 <b>Hay Tseghakron</b>\n\n"
        f"Կազմաձևված՝ <b>{'այո' if settings.deepseek_configured else 'ոչ'}</b>\n"
        f"Մոդել՝ <code>{html.escape(settings.deepseek_model)}</code>\n"
        f"Հարցումներ՝ <b>{stats['requests']}</b>\n"
        f"Prompt tokens՝ <b>{stats['prompt_tokens']}</b>\n"
        f"Completion tokens՝ <b>{stats['completion_tokens']}</b>"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_support")
async def admin_support(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    stats = await asyncio.to_thread(db.get_donation_stats)
    text = (
        "❤️ <b>Աջակցության վիճակագրություն</b>\n\n"
        f"Բոլոր invoice-ները՝ <b>{stats['total_orders']}</b>\n"
        f"Հաստատված՝ <b>{stats['paid_orders']}</b>\n"
        f"Telegram Stars՝ <b>{stats['stars_total']:.0f} XTR</b>\n"
        f"Cryptomus invoice-ներ՝ <b>${stats['crypto_total']:.2f}</b>\n\n"
        "<b>Վերջին գործարքները</b>\n"
    )
    for item in stats.get("recent", [])[:12]:
        provider = "Stars" if item.get("provider") == "telegram_stars" else "Cryptomus"
        text += (
            f"• {html.escape(str(item.get('amount')))} {html.escape(str(item.get('currency')))} · "
            f"{provider} · <code>{html.escape(str(item.get('status')))}</code>\n"
        )
    await callback.message.edit_text(
        text[:3900],
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_backup")
async def admin_backup(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Ներբեռնել SQLite backup", callback_data="admin_download_db")],
        [InlineKeyboardButton(text="📤 Export heroes JSON", callback_data="admin_export_json")],
        [InlineKeyboardButton(text="↩️ Վերադառնալ", callback_data="admin_back")],
    ])
    await callback.message.edit_text("💾 <b>Backup և Export</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_download_db")
async def admin_download_db(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    backup_dir = Path("temp")
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"heroes_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    await asyncio.to_thread(shutil.copy2, db.db_path, path)
    try:
        await callback.message.answer_document(types.FSInputFile(path), caption="SQLite backup")
    finally:
        path.unlink(missing_ok=True)
    await callback.answer()


@router.callback_query(F.data == "admin_clear_cache")
async def admin_clear_cache(callback: types.CallbackQuery) -> None:
    if await _deny(callback):
        return
    await asyncio.to_thread(cache.clear)
    await callback.message.answer("✅ Cache-ը մաքրվեց։", reply_markup=admin_keyboard())
    await callback.answer()


def _plain_text(value: object) -> str:
    import re

    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()
>>>>>>> 54c1deb (commit)
