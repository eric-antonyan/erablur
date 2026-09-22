"""Database-grounded museum AI assistant."""
from __future__ import annotations

import asyncio
import hashlib
import html
import re
import time
from dataclasses import dataclass, field
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from app.config.settings import settings
from app.db.database import db
from app.db.file_cache import cache
from app.services.deepseek import DeepSeekError, deepseek
from app.utils.armenian_search import hero_display_name, normalize_armenian_text

router = Router(name="deepseek_ai")


class AIStates(StatesGroup):
    waiting_question = State()
    waiting_hero_name = State()


@dataclass(slots=True)
class CooldownLimiter:
    cooldown: int
    _last_request: dict[int, float] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def check(self, user_id: int) -> int:
        now = time.monotonic()
        async with self._lock:
            previous = self._last_request.get(user_id, 0.0)
            remaining = self.cooldown - int(now - previous)
            if remaining > 0:
                return remaining
            self._last_request[user_id] = now
            # Avoid unbounded memory growth.
            if len(self._last_request) > 10_000:
                cutoff = now - max(300, self.cooldown * 10)
                self._last_request = {uid: ts for uid, ts in self._last_request.items() if ts >= cutoff}
            return 0


limiter = CooldownLimiter(settings.ai_cooldown_seconds)


def ai_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Հարց տալ թանգարանին", callback_data="ai_ask")],
        [InlineKeyboardButton(text="🧾 Ամփոփել հերոսի պատմությունը", callback_data="ai_summarize")],
        [InlineKeyboardButton(text="🧠 AI վիկտորինա", callback_data="ai_quiz")],
        [InlineKeyboardButton(text="↩️ Վերադառնալ մենյու", callback_data="back_to_menu")],
    ])


async def _show_ai_menu(target: types.Message, *, edit: bool = False) -> None:
    status = "✅ Միացված է" if deepseek.configured else "⚠️ API բանալին կազմաձևված չէ"
    text = (
        "🤖 <b>Hay Tseghakron թանգարանային AI օգնական</b>\n\n"
        "AI-ը պատասխանում է միայն բոտի տեղական թանգարանային գրառումներով։ "
        "Եթե տվյալը չկա, այն չպետք է հորինի։\n\n"
        f"Վիճակ՝ <b>{status}</b>\n"
        f"Օրական սահմանաչափ՝ <b>{settings.ai_daily_limit}</b> հարց"
    )
    if edit:
        await target.edit_text(text, reply_markup=ai_menu_keyboard(), parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=ai_menu_keyboard(), parse_mode="HTML")


@router.message(Command("ai"))
async def ai_command(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await _show_ai_menu(message)


@router.callback_query(F.data == "ai_menu")
async def ai_menu_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await _show_ai_menu(callback.message, edit=True)
    except Exception:
        await _show_ai_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data == "ai_ask")
async def ai_ask_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AIStates.waiting_question)
    await callback.message.answer(
        "💬 Գրեք հարցը հերոսի, պատերազմի, մարզի կամ թանգարանի գրառումներում նկարագրված դեպքի մասին։\n\n"
        "Օրինակ՝ «Պատմիր Ռոբերտ Աբաջյանի մասին»։",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Չեղարկել", callback_data="ai_cancel")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "ai_summarize")
async def ai_summarize_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AIStates.waiting_hero_name)
    await callback.message.answer(
        "🧾 Գրեք հերոսի անունը և ազգանունը։",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Չեղարկել", callback_data="ai_cancel")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "ai_cancel")
async def ai_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Գործողությունը չեղարկվեց։", reply_markup=ai_menu_keyboard())
    await callback.answer()


@router.message(AIStates.waiting_question)
async def ai_question(message: types.Message, state: FSMContext) -> None:
    question = (message.text or "").strip()
    if not question:
        await message.answer("Խնդրում եմ ուղարկել տեքստային հարց։")
        return
    if len(question) > settings.ai_max_question_length:
        await message.answer(f"Հարցը չափազանց երկար է։ Սահմանաչափը {settings.ai_max_question_length} նիշ է։")
        return

    allowed, reason = await _check_access(message.from_user.id)
    if not allowed:
        await message.answer(reason)
        return

    records = await asyncio.to_thread(db.search_heroes_for_context, question, settings.ai_context_heroes)
    if not records:
        await message.answer(
            "Թանգարանի տվյալներում այս հարցին համապատասխան հերոսի գրառում չգտա։ "
            "Փորձեք գրել ամբողջական անունը կամ ավելի հստակ հիմնաբառեր։"
        )
        return

    await state.clear()
    progress = await message.answer("🤖 AI օգնականը վերլուծում է համապատասխան թանգարանային գրառումը…")
    cache_key = _ai_cache_key("answer", question, records)
    cached = cache.get(cache_key)
    if cached:
        await progress.delete()
        await _send_long_text(message, str(cached), footer="\n\n♻️ Պատասխանը վերցվել է տեղական cache-ից։")
        return

    direct_answer = _grounded_fact_answer(question, records)
    if direct_answer:
        cache.set(cache_key, direct_answer, ttl=settings.ai_cache_ttl)
        await asyncio.to_thread(db.record_ai_usage, message.from_user.id, prompt_tokens=0, completion_tokens=0)
        await progress.delete()
        await _send_long_text(message, direct_answer)
        return

    try:
        result = await deepseek.answer_from_records(question, records)
        response = _normalize_ai_text(result.content)
        if _incorrect_missing_claim(response, question, records):
            logger.warning(
                "AI rejected an existing local record for query={!r}; using grounded fallback",
                question,
            )
            response = _grounded_fallback_answer(question, records)
        cache.set(cache_key, response, ttl=settings.ai_cache_ttl)
        await asyncio.to_thread(
            db.record_ai_usage,
            message.from_user.id,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
        await progress.delete()
        await _send_long_text(message, response)
    except DeepSeekError as exc:
        logger.warning("AI question failed for user {}: {}", message.from_user.id, exc)
        await progress.edit_text(f"⚠️ {exc}\n\n" + _offline_matches(records))
    except Exception as exc:
        logger.exception("Unexpected AI question error: {}", exc)
        await progress.edit_text("⚠️ AI հարցման ժամանակ ներքին սխալ առաջացավ։")


@router.message(AIStates.waiting_hero_name)
async def ai_summarize_name(message: types.Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Խնդրում եմ գրել հերոսի անունը։")
        return
    records = await asyncio.to_thread(db.get_heroes_by_name, query, 10)
    if not records:
        await message.answer("Այդ անունով հերոս չգտնվեց։ Փորձեք այլ ուղղագրությամբ։")
        return
    if len(records) > 1:
        buttons = []
        for hero in records[:10]:
            name = f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()
            buttons.append([InlineKeyboardButton(text=name[:55], callback_data=f"ai_explain|{hero['id']}")])
        buttons.append([InlineKeyboardButton(text="❌ Չեղարկել", callback_data="ai_cancel")])
        await state.clear()
        await message.answer("Գտնվել են մի քանի գրառումներ․ ընտրեք հերոսին։", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    await state.clear()
    await _summarize_hero(message, records[0])


@router.callback_query(F.data.startswith("ai_explain|"))
async def ai_explain_hero(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    hero_id = callback.data.split("|", 1)[1]
    hero = await asyncio.to_thread(db.get_hero, hero_id)
    if not hero:
        await callback.answer("Հերոսը չի գտնվել։", show_alert=True)
        return
    await callback.answer("AI ամփոփումը պատրաստվում է…")
    await _summarize_hero(callback.message, hero, user_id=callback.from_user.id)


async def _summarize_hero(message: types.Message, hero: dict, user_id: int | None = None) -> None:
    uid = user_id or message.chat.id
    allowed, reason = await _check_access(uid)
    if not allowed:
        await message.answer(reason)
        return
    name = f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()
    progress = await message.answer(f"🤖 Պատրաստվում է {html.escape(name)}-ի AI ամփոփումը…", parse_mode="HTML")
    cache_key = _ai_cache_key("summary", hero.get("id", ""), [hero])
    cached = cache.get(cache_key)
    if cached:
        await progress.delete()
        await _send_long_text(message, str(cached))
        return
    try:
        result = await deepseek.summarize_hero(hero)
        response = _normalize_ai_text(result.content)
        cache.set(cache_key, response, ttl=settings.ai_cache_ttl)
        await asyncio.to_thread(
            db.record_ai_usage,
            uid,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
        await progress.delete()
        await _send_long_text(message, response)
    except DeepSeekError as exc:
        await progress.edit_text(f"⚠️ {exc}\n\n" + _offline_summary(hero), parse_mode=None)


@router.callback_query(F.data == "ai_quiz")
async def ai_quiz(callback: types.CallbackQuery) -> None:
    allowed, reason = await _check_access(callback.from_user.id)
    if not allowed:
        await callback.answer(reason, show_alert=True)
        return
    await callback.answer("Վիկտորինան պատրաստվում է…")
    records = await asyncio.to_thread(db.get_random_heroes, 8)
    if len(records) < 4:
        await callback.message.answer("Վիկտորինայի համար տվյալները բավարար չեն։")
        return
    progress = await callback.message.answer("🧠 AI օգնականը ստեղծում է հարց թանգարանի տվյալներից…")
    try:
        result, quiz = await deepseek.create_quiz(records)
        await asyncio.to_thread(
            db.record_ai_usage,
            callback.from_user.id,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
    except DeepSeekError as exc:
        logger.warning("AI quiz fallback: {}", exc)
        quiz = _offline_quiz(records)

    quiz_id = uuid4().hex[:10]
    cache.set(f"ai_quiz:{quiz_id}", quiz, ttl=900)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{chr(65 + i)}. {option}"[:60], callback_data=f"ai_quiz_answer|{quiz_id}|{i}")]
        for i, option in enumerate(quiz["options"])
    ] + [[InlineKeyboardButton(text="🔄 Նոր հարց", callback_data="ai_quiz")]])
    await progress.edit_text(f"🧠 <b>AI վիկտորինա</b>\n\n{html.escape(quiz['question'])}", parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("ai_quiz_answer|"))
async def ai_quiz_answer(callback: types.CallbackQuery) -> None:
    try:
        _, quiz_id, selected_raw = callback.data.split("|", 2)
        selected = int(selected_raw)
    except (ValueError, IndexError):
        await callback.answer("Սխալ պատասխան։", show_alert=True)
        return
    quiz = cache.get(f"ai_quiz:{quiz_id}")
    if not quiz:
        await callback.answer("Հարցի ժամկետը սպառվել է։", show_alert=True)
        return
    correct = int(quiz["correct_index"])
    is_correct = selected == correct
    answer = quiz["options"][correct]
    explanation = quiz.get("explanation", "")
    source = quiz.get("source_hero", "")
    text = (
        ("✅ <b>Ճիշտ է</b>" if is_correct else "❌ <b>Սխալ է</b>")
        + f"\n\nՃիշտ պատասխան՝ <b>{html.escape(answer)}</b>"
        + (f"\n\n{html.escape(explanation)}" if explanation else "")
        + (f"\n\nԱղբյուր՝ {html.escape(source)}" if source else "")
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Նոր հարց", callback_data="ai_quiz")],
            [InlineKeyboardButton(text="🤖 AI մենյու", callback_data="ai_menu")],
        ]),
    )
    await callback.answer("Ճիշտ պատասխան" if is_correct else "Սխալ պատասխան")


@router.message(Command("ai_status"))
async def ai_status(message: types.Message) -> None:
    if message.from_user.id not in settings.admin_ids:
        return
    stats = await asyncio.to_thread(db.get_ai_global_stats)
    await message.answer(
        "🤖 <b>AI կարգավիճակ</b>\n\n"
        f"Կազմաձևված՝ <b>{'այո' if deepseek.configured else 'ոչ'}</b>\n"
        f"Մոդել՝ <code>{html.escape(settings.deepseek_model)}</code>\n"
        f"Ընդհանուր հարցումներ՝ <b>{stats['requests']}</b>\n"
        f"Prompt tokens՝ <b>{stats['prompt_tokens']}</b>\n"
        f"Completion tokens՝ <b>{stats['completion_tokens']}</b>",
        parse_mode="HTML",
    )


async def _check_access(user_id: int) -> tuple[bool, str]:
    if not settings.ai_enabled:
        return False, "AI օգնականը ժամանակավորապես անջատված է։"
    remaining = await limiter.check(user_id)
    if remaining > 0:
        return False, f"Խնդրում եմ սպասել մոտ {remaining} վայրկյան և կրկին փորձել։"
    used = await asyncio.to_thread(db.get_ai_usage_count, user_id)
    limit = settings.ai_admin_daily_limit if user_id in settings.admin_ids else settings.ai_daily_limit
    if used >= limit:
        return False, f"Այսօրվա AI սահմանաչափը սպառվել է ({limit}/{limit})։"
    return True, ""



def _question_has_any(question: str, terms: tuple[str, ...]) -> bool:
    normalized = normalize_armenian_text(question)
    return any(normalize_armenian_text(term) in normalized for term in terms)


def _grounded_fact_answer(question: str, records: list[dict]) -> str | None:
    """Answer simple database-field questions without giving the LLM room to drift."""
    if len(records) != 1:
        return None
    hero = records[0]
    name = hero_display_name(hero)
    asks_region = _question_has_any(
        question,
        ("որտեղից էր", "որտեղից է", "որ մարզից", "ինչ մարզից", "ծննդավայր", "որ տարածաշրջանից"),
    )
    asks_war = _question_has_any(
        question,
        ("որ պատերազմի", "ինչ պատերազմի", "պատերազմի մասնակից", "որ պատերազմին", "ինչ պատերազմին"),
    )
    asks_birth = _question_has_any(question, ("երբ է ծնվել", "երբ էր ծնվել", "ծննդյան ամսաթիվ", "ծննդյան տարեթիվ"))
    asks_death = _question_has_any(question, ("երբ է զոհվել", "երբ էր զոհվել", "երբ է մահացել", "մահվան ամսաթիվ"))

    facts: list[str] = []
    if asks_region and str(hero.get("region", "")).strip():
        facts.append(f"📍 Տարածաշրջան՝ {hero['region']}")
    if asks_war and str(hero.get("war", "")).strip():
        facts.append(f"⚔️ Պատերազմ/գործողություն՝ {hero['war']}")
    if asks_birth and str(hero.get("birth_date", "")).strip():
        facts.append(f"📅 Ծննդյան տվյալ՝ {hero['birth_date']}")
    if asks_death and str(hero.get("death_date", "")).strip():
        facts.append(f"🕯️ Մահվան տվյալ՝ {hero['death_date']}")
    if not facts:
        return None

    intro = f"{name}ի թանգարանային գրառման տվյալներն են՝"
    return intro + "\n\n" + "\n".join(facts) + f"\n\nԱղբյուր՝ {name}"


def _incorrect_missing_claim(response: str, question: str, records: list[dict]) -> bool:
    if not records:
        return False
    normalized = normalize_armenian_text(response)
    hard_phrases = (
        "գրառում չկա",
        "չի հիշատակվում",
        "չի գտնվել",
        "հնարավոր չէ տեղեկություն տրամադրել նրա մասին",
    )
    if any(normalize_armenian_text(phrase) in normalized for phrase in hard_phrases):
        return True
    asks_for_person = _question_has_any(question, ("պատմիր", "պատմեք", "ով էր", "մասին", "կենսագրություն"))
    return asks_for_person and normalize_armenian_text("բավարար տեղեկություն չկա") in normalized


def _grounded_fallback_answer(question: str, records: list[dict]) -> str:
    direct = _grounded_fact_answer(question, records)
    if direct:
        return direct
    if len(records) == 1:
        hero = records[0]
        return _offline_summary(hero) + f"\n\nԱղբյուր՝ {hero_display_name(hero)}"
    return _offline_matches(records)


def _ai_cache_key(task: str, query: object, records: list[dict]) -> str:
    ids = ",".join(str(record.get("id", "")) for record in records)
    digest = hashlib.sha256(f"retrieval-v3|{settings.deepseek_model}|{task}|{query}|{ids}".encode("utf-8")).hexdigest()
    return f"deepseek:{digest}"


def _normalize_ai_text(text: str) -> str:
    text = text.replace("```", "").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:12000]


async def _send_long_text(message: types.Message, text: str, footer: str = "") -> None:
    full = text + footer
    while full:
        if len(full) <= 3900:
            chunk, full = full, ""
        else:
            split = full.rfind("\n", 0, 3900)
            if split < 1000:
                split = 3900
            chunk, full = full[:split], full[split:].lstrip()
        await message.answer(chunk, parse_mode=None)


def _clean_bio(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _offline_matches(records: list[dict]) -> str:
    lines = ["Համապատասխան տեղական գրառումներ՝"]
    for hero in records[:5]:
        name = f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()
        lines.append(f"• {name} — {hero.get('region', '—')}, {hero.get('war', '—')}")
    return "\n".join(lines)


def _offline_summary(hero: dict) -> str:
    name = f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()
    bio = _clean_bio(hero.get("bio", ""))
    if len(bio) > 900:
        bio = bio[:897].rsplit(" ", 1)[0] + "…"
    return (
        f"{name}\n"
        f"{hero.get('birth_date', '—')} — {hero.get('death_date', '—')}\n"
        f"Տարածաշրջան՝ {hero.get('region', '—')}\n"
        f"Գործողություն՝ {hero.get('war', '—')}\n\n{bio or 'Կենսագրական տվյալ չկա։'}"
    )


def _offline_quiz(records: list[dict]) -> dict:
    hero = records[0]
    names = [f"{h.get('first_name', '')} {h.get('last_name', '')}".strip() for h in records[:4]]
    return {
        "question": f"Ո՞ր հերոսի գրառման մեջ է նշված «{hero.get('region', 'անհայտ մարզ')}» տարածաշրջանը։",
        "options": names,
        "correct_index": 0,
        "explanation": "Պատասխանը կազմվել է բոտի տեղական տվյալների բազայից։",
        "source_hero": names[0],
    }
