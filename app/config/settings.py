<<<<<<< HEAD
import os
=======
"""Application settings loaded from environment variables.

Secrets must live in ``.env`` or deployment environment variables. Never put
bot tokens, payment keys, wallet seeds, or database credentials in source.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, FrozenSet

>>>>>>> 54c1deb (commit)
from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD
BOT_TOKEN = os.getenv("BOT_TOKEN")

MONGO_URI = os.getenv("MONGO_URI")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASS = os.getenv("REDIS_PASS")
TEST_BOT_TOKEN = os.getenv("TEST_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
=======

def _as_int(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw not in (None, "") else default
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _as_float(name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = os.getenv(name)
    try:
        value = float(raw) if raw not in (None, "") else default
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _as_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _as_int_tuple(name: str, default: tuple[int, ...], *, minimum: int, maximum: int) -> tuple[int, ...]:
    values: list[int] = []
    for part in os.getenv(name, ",".join(map(str, default))).split(","):
        try:
            value = int(part.strip())
        except ValueError:
            continue
        if minimum <= value <= maximum and value not in values:
            values.append(value)
    return tuple(values or default)


def _parse_admin_ids() -> FrozenSet[int]:
    values = {os.getenv("OWNER_ID", "0"), *os.getenv("ADMIN_IDS", "").split(",")}
    result: set[int] = set()
    for value in values:
        value = value.strip()
        if value.lstrip("-").isdigit() and int(value) > 0:
            result.add(int(value))
    return frozenset(result)


def _parse_extra_payment_methods() -> tuple[dict[str, str], ...]:
    raw = os.getenv("EXTRA_PAYMENT_METHODS_JSON", "").strip()
    if not raw:
        return ()
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, list):
        return ()
    methods: list[dict[str, str]] = []
    for item in payload[:8]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:48]
        url = str(item.get("url") or "").strip()
        if title and url.startswith("https://"):
            methods.append({"title": title, "url": url})
    return tuple(methods)


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN")
    owner_id: int = _as_int("OWNER_ID", 0, minimum=0)
    admin_ids: FrozenSet[int] = _parse_admin_ids()
    bot_username: str = os.getenv("BOT_USERNAME", "erablurbot").strip().lstrip("@")
    webapp_url: str = os.getenv("WEBAPP_URL", "").strip().rstrip("/")

    database_path: str = os.getenv("DATABASE_PATH", "data/heroes.db").strip()
    mongodb_url: str = os.getenv("MONGODB_URL", "").strip()
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "erablur").strip() or "erablur"
    mongodb_required: bool = _as_bool("MONGODB_REQUIRED", False)
    mongodb_timeout_ms: int = _as_int("MONGODB_TIMEOUT_MS", 5000, minimum=1000, maximum=60000)
    cache_dir: str = os.getenv("CACHE_DIR", "data/cache").strip()
    cache_ttl: int = _as_int("CACHE_TTL", 3600, minimum=60)
    max_cache_items: int = _as_int("MAX_CACHE_ITEMS", 1000, minimum=50)

    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
    deepseek_timeout: float = _as_float("DEEPSEEK_TIMEOUT", 45.0, minimum=5.0)
    deepseek_max_retries: int = _as_int("DEEPSEEK_MAX_RETRIES", 3, minimum=1, maximum=5)
    deepseek_max_concurrency: int = _as_int("DEEPSEEK_MAX_CONCURRENCY", 3, minimum=1, maximum=20)

    ai_enabled: bool = _as_bool("AI_ENABLED", True)
    ai_daily_limit: int = _as_int("AI_DAILY_LIMIT", 20, minimum=1, maximum=500)
    ai_admin_daily_limit: int = _as_int("AI_ADMIN_DAILY_LIMIT", 200, minimum=1, maximum=5000)
    ai_cooldown_seconds: int = _as_int("AI_COOLDOWN_SECONDS", 8, minimum=1, maximum=300)
    ai_max_question_length: int = _as_int("AI_MAX_QUESTION_LENGTH", 700, minimum=80, maximum=4000)
    ai_context_heroes: int = _as_int("AI_CONTEXT_HEROES", 6, minimum=1, maximum=12)
    ai_cache_ttl: int = _as_int("AI_CACHE_TTL", 21600, minimum=60)

    # Voluntary project support. No paid feature is unlocked by a contribution.
    support_enabled: bool = _as_bool("SUPPORT_ENABLED", True)
    support_contact: str = os.getenv("SUPPORT_CONTACT", "").strip()
    support_project_name: str = os.getenv("SUPPORT_PROJECT_NAME", "Հայոց Հերոսներ").strip()[:64]
    support_note: str = os.getenv(
        "SUPPORT_NOTE",
        "Աջակցությունը կամավոր է և չի բացում վճարովի հնարավորություն։",
    ).strip()[:500]
    stars_amounts: tuple[int, ...] = _as_int_tuple(
        "TELEGRAM_STARS_AMOUNTS", (50, 100, 250, 500), minimum=1, maximum=100000
    )
    crypto_amounts_usd: tuple[int, ...] = _as_int_tuple(
        "CRYPTO_AMOUNTS_USD", (5, 10, 25, 50), minimum=1, maximum=10000
    )
    crypto_min_usd: float = _as_float("CRYPTO_MIN_USD", 1.0, minimum=0.1, maximum=10000.0)
    crypto_max_usd: float = _as_float("CRYPTO_MAX_USD", 10000.0, minimum=1.0, maximum=1000000.0)

    cryptomus_merchant_id: str = os.getenv("CRYPTOMUS_MERCHANT_ID", "").strip()
    cryptomus_payment_key: str = os.getenv("CRYPTOMUS_PAYMENT_KEY", "").strip()
    cryptomus_base_url: str = os.getenv("CRYPTOMUS_BASE_URL", "https://api.cryptomus.com").rstrip("/")
    cryptomus_timeout: float = _as_float("CRYPTOMUS_TIMEOUT", 25.0, minimum=5.0, maximum=120.0)
    cryptomus_invoice_currency: str = os.getenv("CRYPTOMUS_INVOICE_CURRENCY", "USD").strip().upper()
    cryptomus_to_currency: str = os.getenv("CRYPTOMUS_TO_CURRENCY", "USDT").strip().upper()
    cryptomus_network: str = os.getenv("CRYPTOMUS_NETWORK", "").strip().lower()
    cryptomus_lifetime: int = _as_int("CRYPTOMUS_LIFETIME", 3600, minimum=300, maximum=43200)
    cryptomus_return_url: str = os.getenv("CRYPTOMUS_RETURN_URL", "").strip()
    cryptomus_success_url: str = os.getenv("CRYPTOMUS_SUCCESS_URL", "").strip()
    cryptomus_callback_url: str = os.getenv("CRYPTOMUS_CALLBACK_URL", "").strip()
    cryptomus_verify_ip: bool = _as_bool("CRYPTOMUS_VERIFY_IP", False)

    payment_webhook_enabled: bool = _as_bool("PAYMENT_WEBHOOK_ENABLED", False)
    payment_webhook_host: str = os.getenv("PAYMENT_WEBHOOK_HOST", "0.0.0.0").strip()
    payment_webhook_port: int = _as_int("PAYMENT_WEBHOOK_PORT", _as_int("PORT", 8080, minimum=1, maximum=65535), minimum=1, maximum=65535)
    payment_webhook_path_secret: str = os.getenv("PAYMENT_WEBHOOK_PATH_SECRET", "").strip()

    bank_card_payment_url: str = os.getenv("BANK_CARD_PAYMENT_URL", "").strip()
    bank_card_label: str = os.getenv("BANK_CARD_LABEL", "💳 Քարտով աջակցել").strip()[:48]
    extra_payment_methods: tuple[dict[str, str], ...] = _parse_extra_payment_methods()

    schedule_hour: int = _as_int("DAILY_POST_HOUR", 16, minimum=0, maximum=23)
    schedule_minute: int = _as_int("DAILY_POST_MINUTE", 30, minimum=0, maximum=59)
    timezone: str = os.getenv("TIMEZONE", "Asia/Yerevan").strip()
    log_level: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    @property
    def mongodb_configured(self) -> bool:
        return bool(self.mongodb_url)

    @property
    def deepseek_configured(self) -> bool:
        return self.ai_enabled and bool(self.deepseek_api_key)

    @property
    def cryptomus_configured(self) -> bool:
        return bool(self.cryptomus_merchant_id and self.cryptomus_payment_key)

    @property
    def webhook_configured(self) -> bool:
        return bool(
            self.payment_webhook_enabled
            and self.payment_webhook_path_secret
            and self.cryptomus_configured
        )

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and configure it.")
        if self.crypto_max_usd < self.crypto_min_usd:
            raise RuntimeError("CRYPTO_MAX_USD must be greater than or equal to CRYPTO_MIN_USD.")
        if self.payment_webhook_enabled and not self.payment_webhook_path_secret:
            raise RuntimeError("PAYMENT_WEBHOOK_PATH_SECRET is required when PAYMENT_WEBHOOK_ENABLED=true.")
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
        Path("temp").mkdir(parents=True, exist_ok=True)


settings = Settings()

# Backward-compatible constants used by existing handlers.
BOT_TOKEN = settings.bot_token
OWNER_ID = settings.owner_id
ADMIN_IDS = settings.admin_ids
DATABASE_PATH = settings.database_path
MONGODB_URL = settings.mongodb_url
MONGODB_DB_NAME = settings.mongodb_db_name
CACHE_TTL = settings.cache_ttl
MAX_CACHE_ITEMS = settings.max_cache_items
>>>>>>> 54c1deb (commit)
