"""Async DeepSeek API client with retries, concurrency control and safe output."""
from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from typing import Any, Iterable

import httpx
from loguru import logger

from app.config.settings import settings


class DeepSeekError(RuntimeError):
    """A user-safe DeepSeek integration error."""


@dataclass(slots=True)
class DeepSeekResult:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class DeepSeekClient:
    RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(settings.deepseek_max_concurrency)
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    @property
    def configured(self) -> bool:
        return settings.deepseek_configured

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.deepseek_base_url,
                timeout=httpx.Timeout(settings.deepseek_timeout, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "armenian-heroes-museum-bot/2.0",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int = 900,
        temperature: float = 0.2,
        json_mode: bool = False,
        thinking: bool = False,
    ) -> DeepSeekResult:
        if not self.configured:
            raise DeepSeekError("Hay Tseghakron-ը կազմաձևված չէ։")

        loop = asyncio.get_running_loop()
        if loop.time() < self._circuit_open_until:
            raise DeepSeekError("AI ծառայությունը ժամանակավորապես դադարեցված է բազմաթիվ սխալներից հետո։")

        payload: dict[str, Any] = {
            "model": settings.deepseek_model,
            "messages": list(messages),
            "max_tokens": max(100, min(max_tokens, 4000)),
            "stream": False,
            # V4 defaults to thinking enabled. Disable it for quick museum Q&A
            # and avoid returning/internalizing reasoning content unnecessarily.
            "thinking": {"type": "enabled" if thinking else "disabled"},
        }
        if not thinking:
            payload["temperature"] = max(0.0, min(temperature, 1.5))
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        async with self._semaphore:
            for attempt in range(settings.deepseek_max_retries):
                try:
                    response = await self._get_client().post("/chat/completions", json=payload)
                    if response.status_code in self.RETRYABLE_STATUS:
                        raise _RetryableHTTPError(response.status_code, response.text[:300])
                    response.raise_for_status()
                    data = response.json()
                    choices = data.get("choices") or []
                    if not choices:
                        raise _RetryableHTTPError(200, "empty choices")
                    content = ((choices[0].get("message") or {}).get("content") or "").strip()
                    if not content:
                        raise _RetryableHTTPError(200, "empty content")
                    usage = data.get("usage") or {}
                    self._consecutive_failures = 0
                    return DeepSeekResult(
                        content=content,
                        prompt_tokens=int(usage.get("prompt_tokens") or 0),
                        completion_tokens=int(usage.get("completion_tokens") or 0),
                        model=str(data.get("model") or settings.deepseek_model),
                    )
                except _RetryableHTTPError as exc:
                    last_error = exc
                    if attempt + 1 < settings.deepseek_max_retries:
                        delay = min(8.0, (2**attempt) + random.random())
                        logger.warning("DeepSeek retryable HTTP {} (attempt {}/{})", exc.status, attempt + 1, settings.deepseek_max_retries)
                        await asyncio.sleep(delay)
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt + 1 < settings.deepseek_max_retries:
                        await asyncio.sleep(min(8.0, (2**attempt) + random.random()))
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    detail = _extract_error(exc.response)
                    if status == 401:
                        raise DeepSeekError("AI ծառայության API բանալին սխալ է կամ անվավեր։") from exc
                    if status == 402:
                        raise DeepSeekError("AI ծառայության հաշվի մնացորդը բավարար չէ։") from exc
                    if status == 422:
                        raise DeepSeekError(f"AI հարցման սխալ պարամետր՝ {detail}") from exc
                    raise DeepSeekError(f"AI ծառայության սխալ ({status})։") from exc
                except (ValueError, json.JSONDecodeError) as exc:
                    last_error = exc
                    break

        self._consecutive_failures += 1
        if self._consecutive_failures >= 5:
            self._circuit_open_until = asyncio.get_running_loop().time() + 60
        logger.error("DeepSeek request failed: {}", repr(last_error))
        raise DeepSeekError("AI ծառայությունը հիմա հասանելի չէ։ Փորձեք մի փոքր ուշ։") from last_error

    async def answer_from_records(self, question: str, records: list[dict[str, Any]]) -> DeepSeekResult:
        context = _records_to_context(records)
        system = (
            "Դու «Հայոց Հերոսներ» բոտի ճշգրիտ հետազոտական օգնականն ես։ "
            "Պատասխանիր միայն հայերենով և միայն PROVIDED_MUSEUM_RECORDS բաժնում տրված տվյալներով։ "
            "Տեղական որոնման համակարգն արդեն ընտրել է հարցին համապատասխան գրառումները։ եթե հարցում նշված անունը համընկնում է "
            "RECORD-ի «Անուն» դաշտին, անմիջապես պատասխանիր այդ գրառումից և երբեք մի ասա, թե այդ հերոսի գրառում չկա։ "
            "Մի շփոթիր նույն անունն ունեցող տարբեր մարդկանց և մի թվարկիր չօգտագործված գրառումներ։ "
            "Մի հորինիր անուն, ամսաթիվ, կոչում, դեպք կամ պատճառ։ Եթե ընտրված գրառման տվյալը իսկապես չի բավարարում, հստակ ասա՝ "
            "«Թանգարանի տվյալներում բավարար տեղեկություն չկա»։ Տարբերակիր արձանագրված փաստը մեկնաբանությունից։ "
            "Պահպանիր հարգալից, չեզոք լեզու, մի՛ օգտագործիր ատելության խոսք կամ բռնության կոչեր։ "
            "Պատասխանի վերջում գրիր «Աղբյուրներ՝» և թվարկիր օգտագործված հերոսների անունները։ "
            "Պատասխանը պահիր առավելագույնը 350 բառ։"
        )
        user = f"PROVIDED_MUSEUM_RECORDS:\n{context}\n\nUSER_QUESTION:\n{question}"
        return await self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=1100,
            temperature=0.1,
            thinking=False,
        )

    async def summarize_hero(self, record: dict[str, Any]) -> DeepSeekResult:
        system = (
            "Դու թանգարանային խմբագիր ես։ Միայն տրամադրված գրառումից կազմիր հայերեն, հարգալից և ճշգրիտ ամփոփում։ "
            "Չավելացնես արտաքին փաստեր։ Կառուցվածքը՝ 1) Ով էր, 2) Կյանքի հիմնական դրվագներ, 3) Հիշատակի մեկ նախադասություն։ "
            "Առավելագույնը 220 բառ։ Մի օգտագործիր Markdown աղյուսակ։"
        )
        return await self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": _records_to_context([record])}],
            max_tokens=800,
            temperature=0.15,
            thinking=False,
        )

    async def create_quiz(self, records: list[dict[str, Any]]) -> tuple[DeepSeekResult, dict[str, Any]]:
        system = (
            "Տրված թանգարանային գրառումներից ստեղծիր մեկ բազմընտրանի հարց և վերադարձրու միայն JSON։ "
            "JSON ձևաչափը՝ {\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],"
            "\"correct_index\":0,\"explanation\":\"...\",\"source_hero\":\"...\"}. "
            "Պետք է լինի ուղիղ 4 տարբերակ, correct_index-ը՝ 0-3, և բոլոր փաստերը միայն տրված գրառումներից։"
        )
        result = await self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": "JSON INPUT RECORDS:\n" + _records_to_context(records)}],
            max_tokens=700,
            temperature=0.35,
            json_mode=True,
            thinking=False,
        )
        try:
            payload = json.loads(result.content)
            options = payload.get("options")
            correct = int(payload.get("correct_index"))
            if not isinstance(options, list) or len(options) != 4 or not 0 <= correct <= 3:
                raise ValueError("invalid quiz schema")
            payload["question"] = str(payload.get("question", "")).strip()
            payload["options"] = [str(x).strip() for x in options]
            payload["explanation"] = str(payload.get("explanation", "")).strip()
            payload["source_hero"] = str(payload.get("source_hero", "")).strip()
            if not payload["question"] or any(not option for option in payload["options"]):
                raise ValueError("empty quiz values")
            return result, payload
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise DeepSeekError("AI-ը չկարողացավ ճիշտ ձևաչափով վիկտորինա ստեղծել։") from exc


class _RetryableHTTPError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


def _extract_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        error = body.get("error") or {}
        return str(error.get("message") or body)[:250]
    except Exception:
        return response.text[:250]


def _clean_html(value: Any) -> str:
    import html
    import re

    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _records_to_context(records: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, hero in enumerate(records, 1):
        name = f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()
        bio = _clean_html(hero.get("bio", ""))[:5000]
        blocks.append(
            f"[RECORD {index}]\n"
            f"ID: {hero.get('id', '')}\n"
            f"Անուն: {name}\n"
            f"Ծննդյան տվյալ: {hero.get('birth_date', '')}\n"
            f"Մահվան տվյալ: {hero.get('death_date', '')}\n"
            f"Տարածաշրջան: {hero.get('region', '')}\n"
            f"Պատերազմ/գործողություն: {hero.get('war', '')}\n"
            f"Կենսագրություն: {bio}\n"
            f"Սկզբնաղբյուր: {hero.get('bio_link', '')}"
        )
    return "\n\n".join(blocks)


deepseek = DeepSeekClient()
