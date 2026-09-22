"""Thread-safe SQLite data access layer with optional MongoDB runtime selection.

``Database`` remains the SQLite implementation used by tests and local fallback.
When ``MONGODB_URL`` is configured, the module-level ``db`` object is created
from :class:`MongoDatabase` instead, preserving the same handler-facing API.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from loguru import logger

from app.config.settings import DATABASE_PATH
from app.utils.armenian_search import (
    QUESTION_STOPWORDS,
    armenian_tokens,
    hero_display_name,
    normalize_armenian_text,
    rank_hero_name_candidates,
)


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._write_lock = threading.RLock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        conn.create_function("CASEFOLD", 1, lambda value: str(value or "").casefold(), deterministic=True)
        return conn

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        lock = self._write_lock if write else _NullLock()
        with lock:
            conn = self._connect()
            try:
                yield conn
                if write:
                    conn.commit()
            except Exception:
                if write:
                    conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._connection(write=True) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS heroes (
                    id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL DEFAULT '',
                    last_name TEXT NOT NULL DEFAULT '',
                    birth_date TEXT,
                    death_date TEXT,
                    region TEXT,
                    war TEXT,
                    img_url TEXT,
                    bio_link TEXT,
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    search_count INTEGER DEFAULT 0,
                    last_query TEXT,
                    joined_at TIMESTAMP,
                    updated_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    hero_id TEXT,
                    hero_name TEXT,
                    searched_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id INTEGER PRIMARY KEY,
                    title TEXT,
                    owner_id TEXT NOT NULL,
                    connected_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_usage (
                    user_id TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    last_request_at TIMESTAMP,
                    PRIMARY KEY (user_id, usage_date)
                );
                CREATE TABLE IF NOT EXISTS donations (
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    anonymous INTEGER NOT NULL DEFAULT 1,
                    provider_payment_id TEXT,
                    telegram_charge_id TEXT,
                    invoice_url TEXT,
                    paid_amount TEXT,
                    paid_currency TEXT,
                    network TEXT,
                    txid TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    paid_at TIMESTAMP,
                    notified_at TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_heroes_name ON heroes(first_name, last_name);
                CREATE INDEX IF NOT EXISTS idx_heroes_war ON heroes(war);
                CREATE INDEX IF NOT EXISTS idx_heroes_region ON heroes(region);
                CREATE INDEX IF NOT EXISTS idx_history_user_date ON search_history(user_id, searched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_users_search_count ON users(search_count DESC);
                CREATE INDEX IF NOT EXISTS idx_channels_owner ON channels(owner_id);
                CREATE INDEX IF NOT EXISTS idx_donations_user ON donations(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_donations_status ON donations(status, created_at DESC);
                """
            )
            # Older bundled DBs do not have updated_at on heroes.
            columns = {row[1] for row in conn.execute("PRAGMA table_info(heroes)")}
            if "updated_at" not in columns:
                conn.execute("ALTER TABLE heroes ADD COLUMN updated_at TIMESTAMP")
        logger.info("SQLite initialized: {}", self.db_path)

    @staticmethod
    def _row(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
        return dict(row) if row is not None else None

    @staticmethod
    def _rows(rows: Sequence[sqlite3.Row]) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows]

    def ping(self) -> bool:
        try:
            with self._connection() as conn:
                return conn.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    # Heroes -----------------------------------------------------------------
    def save_hero(self, hero_id: str, data: Dict[str, Any]) -> None:
        nested_name = data.get("name") if isinstance(data.get("name"), dict) else {}
        nested_date = data.get("date") if isinstance(data.get("date"), dict) else {}
        payload = {
            "id": str(hero_id),
            "first_name": str(nested_name.get("first", data.get("first_name", "")) or "").strip(),
            "last_name": str(nested_name.get("last", data.get("last_name", "")) or "").strip(),
            "birth_date": str(nested_date.get("birth", data.get("birth_date", "")) or "").strip(),
            "death_date": str(nested_date.get("dead", data.get("death_date", "")) or "").strip(),
            "region": str(data.get("region", "") or "").strip(),
            "war": str(data.get("war", "") or "").strip(),
            "img_url": str(data.get("img_url", "") or "").strip(),
            "bio_link": str(data.get("bio_link", "") or "").strip(),
            "bio": str(data.get("bio", "") or "").strip(),
            "now": datetime.now().isoformat(timespec="seconds"),
        }
        with self._connection(write=True) as conn:
            conn.execute(
                """
                INSERT INTO heroes (
                    id, first_name, last_name, birth_date, death_date, region,
                    war, img_url, bio_link, bio, created_at, updated_at
                ) VALUES (
                    :id, :first_name, :last_name, :birth_date, :death_date, :region,
                    :war, :img_url, :bio_link, :bio, :now, :now
                )
                ON CONFLICT(id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    birth_date=excluded.birth_date,
                    death_date=excluded.death_date,
                    region=excluded.region,
                    war=excluded.war,
                    img_url=excluded.img_url,
                    bio_link=excluded.bio_link,
                    bio=excluded.bio,
                    updated_at=excluded.updated_at
                """,
                payload,
            )

    def get_hero(self, hero_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            return self._row(conn.execute("SELECT * FROM heroes WHERE id = ?", (str(hero_id),)).fetchone())

    def delete_hero(self, hero_id: str) -> bool:
        with self._connection(write=True) as conn:
            cur = conn.execute("DELETE FROM heroes WHERE id = ?", (str(hero_id),))
            return cur.rowcount > 0

    def get_heroes_by_name(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Find heroes by direct name or by a name embedded in a sentence.

        Matching is Armenian-aware: ``Սևակ`` matches the stored ``Սեվակ`` and
        inflected forms such as ``Աբաջյանի`` match ``Աբաջյան``.
        """
        query = " ".join((query or "").strip().split())
        if not query:
            return []
        limit = max(1, min(int(limit), 200))
        heroes = self.get_all_heroes()
        ranked = rank_hero_name_candidates(query, heroes)
        if not ranked:
            return []

        best = ranked[0][0]
        query_tokens = armenian_tokens(query, drop_stopwords=True)
        if len(query_tokens) <= 1:
            threshold = 640.0 if best >= 640.0 else best - 2.0
        elif best >= 900.0:
            # For an explicit full name, return only that person (plus an exact
            # duplicate record with the same display name, if one exists).
            best_name = normalize_armenian_text(hero_display_name(ranked[0][1]))
            return [hero for score, hero in ranked if score >= 900.0 and normalize_armenian_text(hero_display_name(hero)) == best_name][:limit]
        else:
            threshold = max(760.0, best - 35.0)
        return [hero for score, hero in ranked if score >= threshold][:limit]

    def get_heroes_by_names(self, first_name: str, last_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_heroes_by_name(f"{first_name} {last_name}", limit=limit)

    def search_heroes_for_context(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Retrieve a small, accurately ranked local context for an AI question.

        Full-name resolution is attempted first. Only when no confident person
        is mentioned do we perform broader region/war/biography retrieval.
        """
        normalized = normalize_armenian_text(query)
        if not normalized:
            return []
        limit = max(1, min(int(limit), 12))
        heroes = self.get_all_heroes()

        # 1) Resolve an explicitly named hero before any broad keyword search.
        ranked_names = rank_hero_name_candidates(query, heroes)
        if ranked_names:
            best_score, best_hero = ranked_names[0]
            if best_score >= 900.0:
                best_name = normalize_armenian_text(hero_display_name(best_hero))
                exact = [
                    hero for score, hero in ranked_names
                    if score >= 900.0 and normalize_armenian_text(hero_display_name(hero)) == best_name
                ]
                return exact[:limit]
            if best_score >= 875.0 and (len(ranked_names) == 1 or best_score - ranked_names[1][0] >= 25.0):
                return [best_hero]

        # 2) Broader museum search for questions about a war, region, date, etc.
        tokens = [
            token for token in armenian_tokens(query, drop_stopwords=True)
            if len(token) >= 3 and token not in QUESTION_STOPWORDS
        ]
        tokens = list(dict.fromkeys(tokens))[:12]
        if not tokens:
            return []

        scored: list[tuple[float, Dict[str, Any]]] = []
        for hero in heroes:
            name = normalize_armenian_text(hero_display_name(hero))
            region = normalize_armenian_text(hero.get("region", ""))
            war = normalize_armenian_text(hero.get("war", ""))
            bio = normalize_armenian_text(hero.get("bio", ""))
            points = 0.0
            matched = 0
            for token in tokens:
                token_points = 0.0
                if token in name:
                    token_points += 18.0
                if token in region:
                    token_points += 8.0
                if token in war:
                    token_points += 8.0
                if token in bio:
                    token_points += min(4.0, float(bio.count(token)))
                if token_points:
                    matched += 1
                    points += token_points
            if points > 0:
                # Reward records matching more distinct query concepts.
                points += matched * 3.0
                scored.append((points, hero))

        scored.sort(key=lambda item: (-item[0], normalize_armenian_text(hero_display_name(item[1])), str(item[1].get("id", ""))))
        return [hero for _, hero in scored[:limit]]

    def get_heroes_by_war(self, war: str) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            return self._rows(conn.execute(
                "SELECT * FROM heroes WHERE war = ? ORDER BY first_name, last_name", (war,)
            ).fetchall())

    def get_all_heroes(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            return self._rows(conn.execute("SELECT * FROM heroes ORDER BY first_name, last_name").fetchall())

    def get_random_heroes(self, limit: int = 6) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 20))
        with self._connection() as conn:
            return self._rows(conn.execute("SELECT * FROM heroes ORDER BY RANDOM() LIMIT ?", (limit,)).fetchall())

    def count_heroes(self) -> int:
        with self._connection() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM heroes").fetchone()[0])

    def get_all_wars(self) -> List[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT DISTINCT war FROM heroes WHERE TRIM(COALESCE(war, '')) <> '' ORDER BY war").fetchall()
        return [row[0] for row in rows]

    # Users and history -------------------------------------------------------
    def save_user(self, user_id: str, username: str, first_name: str, last_name: str = "") -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connection(write=True) as conn:
            conn.execute(
                """
                INSERT INTO users(id, username, first_name, last_name, search_count, joined_at, updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(id) DO UPDATE SET username=excluded.username,
                    first_name=excluded.first_name, last_name=excluded.last_name,
                    updated_at=excluded.updated_at
                """,
                (str(user_id), username, first_name, last_name, now, now),
            )

    def get_user(self, user_id: str | int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            return self._row(conn.execute("SELECT * FROM users WHERE id = ?", (str(user_id),)).fetchone())

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        username = username.strip().lstrip("@")
        with self._connection() as conn:
            return self._row(conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone())

    def get_all_users(self, limit: int | None = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM users ORDER BY updated_at DESC"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (max(1, min(int(limit), 100000)),)
        with self._connection() as conn:
            return self._rows(conn.execute(sql, params).fetchall())

    def increment_search_count(self, user_id: str, query: str) -> None:
        with self._connection(write=True) as conn:
            conn.execute(
                "UPDATE users SET search_count = COALESCE(search_count, 0) + 1, last_query = ?, updated_at = ? WHERE id = ?",
                (query, datetime.now().isoformat(timespec="seconds"), str(user_id)),
            )

    def add_search_history(self, user_id: str, query: str, hero_id: str, hero_name: str) -> None:
        with self._connection(write=True) as conn:
            conn.execute(
                "INSERT INTO search_history(user_id, query, hero_id, hero_name, searched_at) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), query, str(hero_id), hero_name, datetime.now().isoformat(timespec="seconds")),
            )

    def get_user_search_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            return self._rows(conn.execute(
                "SELECT * FROM search_history WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
                (str(user_id), max(1, min(int(limit), 100))),
            ).fetchall())

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.get_user_search_history(user_id, limit)

    def clear_user_history(self, user_id: str) -> int:
        with self._connection(write=True) as conn:
            cur = conn.execute("DELETE FROM search_history WHERE user_id = ?", (str(user_id),))
            return cur.rowcount

    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            return self._rows(conn.execute(
                "SELECT query, COUNT(*) AS count FROM search_history GROUP BY query ORDER BY count DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall())

    def get_global_stats(self) -> Dict[str, Any]:
        with self._connection() as conn:
            total_users = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
            total_searches = int(conn.execute("SELECT COALESCE(SUM(search_count), 0) FROM users").fetchone()[0])
            total_heroes = int(conn.execute("SELECT COUNT(*) FROM heroes").fetchone()[0])
            top_users = self._rows(conn.execute(
                "SELECT * FROM users ORDER BY search_count DESC, updated_at DESC LIMIT 5"
            ).fetchall())
            last_user = self._row(conn.execute("SELECT * FROM users ORDER BY updated_at DESC LIMIT 1").fetchone())
        return {
            "total_users": total_users,
            "total_searches": total_searches,
            "total_heroes": total_heroes,
            "last_user": last_user,
            "top_users": top_users,
        }

    # Channels ---------------------------------------------------------------
    def save_channel(self, channel_id: int, title: str, owner_id: str) -> None:
        with self._connection(write=True) as conn:
            conn.execute(
                """
                INSERT INTO channels(channel_id, title, owner_id, connected_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET title=excluded.title,
                    owner_id=excluded.owner_id, connected_at=excluded.connected_at
                """,
                (int(channel_id), title, str(owner_id), datetime.now().isoformat(timespec="seconds")),
            )

    @staticmethod
    def _channel_compat(row: Dict[str, Any]) -> Dict[str, Any]:
        row["id"] = row.get("channel_id")
        return row

    def get_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = self._row(conn.execute("SELECT * FROM channels WHERE channel_id = ?", (int(channel_id),)).fetchone())
        return self._channel_compat(row) if row else None

    def get_user_channels(self, owner_id: str) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = self._rows(conn.execute(
                "SELECT * FROM channels WHERE owner_id = ? ORDER BY connected_at DESC", (str(owner_id),)
            ).fetchall())
        return [self._channel_compat(row) for row in rows]

    def get_all_channels(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = self._rows(conn.execute("SELECT * FROM channels ORDER BY connected_at DESC").fetchall())
        return [self._channel_compat(row) for row in rows]

    def delete_channel(self, channel_id: int) -> bool:
        with self._connection(write=True) as conn:
            cur = conn.execute("DELETE FROM channels WHERE channel_id = ?", (int(channel_id),))
            return cur.rowcount > 0

    # Voluntary support / payments -------------------------------------------
    def create_donation(
        self,
        order_id: str,
        *,
        user_id: str | int,
        provider: str,
        amount: str,
        currency: str,
        status: str = "pending",
        anonymous: bool = True,
        provider_payment_id: str = "",
        invoice_url: str = "",
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connection(write=True) as conn:
            conn.execute(
                """
                INSERT INTO donations(
                    order_id, user_id, provider, amount, currency, status, anonymous,
                    provider_payment_id, invoice_url, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    status=excluded.status,
                    provider_payment_id=CASE WHEN excluded.provider_payment_id <> '' THEN excluded.provider_payment_id ELSE donations.provider_payment_id END,
                    invoice_url=CASE WHEN excluded.invoice_url <> '' THEN excluded.invoice_url ELSE donations.invoice_url END,
                    updated_at=excluded.updated_at
                """,
                (
                    str(order_id), str(user_id), provider, str(amount), currency, status,
                    1 if anonymous else 0, provider_payment_id, invoice_url, now, now,
                ),
            )

    def get_donation(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            return self._row(conn.execute(
                "SELECT * FROM donations WHERE order_id = ?", (str(order_id),)
            ).fetchone())

    def get_user_donations(self, user_id: str | int, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            return self._rows(conn.execute(
                "SELECT * FROM donations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (str(user_id), max(1, min(int(limit), 100))),
            ).fetchall())

    def update_donation(
        self,
        order_id: str,
        *,
        status: str,
        provider_payment_id: str = "",
        telegram_charge_id: str = "",
        invoice_url: str = "",
        paid_amount: str = "",
        paid_currency: str = "",
        network: str = "",
        txid: str = "",
        mark_paid: bool = False,
    ) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        paid_at = now if mark_paid else None
        with self._connection(write=True) as conn:
            cur = conn.execute(
                """
                UPDATE donations SET
                    status = ?,
                    provider_payment_id = CASE WHEN ? <> '' THEN ? ELSE provider_payment_id END,
                    telegram_charge_id = CASE WHEN ? <> '' THEN ? ELSE telegram_charge_id END,
                    invoice_url = CASE WHEN ? <> '' THEN ? ELSE invoice_url END,
                    paid_amount = CASE WHEN ? <> '' THEN ? ELSE paid_amount END,
                    paid_currency = CASE WHEN ? <> '' THEN ? ELSE paid_currency END,
                    network = CASE WHEN ? <> '' THEN ? ELSE network END,
                    txid = CASE WHEN ? <> '' THEN ? ELSE txid END,
                    paid_at = CASE WHEN ? IS NOT NULL THEN COALESCE(paid_at, ?) ELSE paid_at END,
                    updated_at = ?
                WHERE order_id = ?
                """,
                (
                    status,
                    provider_payment_id, provider_payment_id,
                    telegram_charge_id, telegram_charge_id,
                    invoice_url, invoice_url,
                    paid_amount, paid_amount,
                    paid_currency, paid_currency,
                    network, network,
                    txid, txid,
                    paid_at, paid_at,
                    now, str(order_id),
                ),
            )
            return cur.rowcount > 0

    def mark_donation_notified(self, order_id: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connection(write=True) as conn:
            conn.execute(
                "UPDATE donations SET notified_at = COALESCE(notified_at, ?), updated_at = ? WHERE order_id = ?",
                (now, now, str(order_id)),
            )

    def get_donation_stats(self) -> Dict[str, Any]:
        with self._connection() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_orders,
                    SUM(CASE WHEN status IN ('paid','paid_over','completed') THEN 1 ELSE 0 END) AS paid_orders,
                    SUM(CASE WHEN provider = 'telegram_stars' AND status = 'completed' THEN CAST(amount AS REAL) ELSE 0 END) AS stars_total,
                    SUM(CASE WHEN provider = 'cryptomus' AND status IN ('paid','paid_over') THEN CAST(amount AS REAL) ELSE 0 END) AS crypto_total
                FROM donations
                """
            ).fetchone()
            recent = self._rows(conn.execute(
                "SELECT * FROM donations ORDER BY created_at DESC LIMIT 15"
            ).fetchall())
        return {
            "total_orders": int(totals[0] or 0),
            "paid_orders": int(totals[1] or 0),
            "stars_total": float(totals[2] or 0),
            "crypto_total": float(totals[3] or 0),
            "recent": recent,
        }

    # AI usage ---------------------------------------------------------------
    def get_ai_usage_count(self, user_id: str | int, usage_date: date | None = None) -> int:
        day = (usage_date or date.today()).isoformat()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT request_count FROM ai_usage WHERE user_id = ? AND usage_date = ?",
                (str(user_id), day),
            ).fetchone()
        return int(row[0]) if row else 0

    def record_ai_usage(
        self,
        user_id: str | int,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        usage_date: date | None = None,
    ) -> None:
        day = (usage_date or date.today()).isoformat()
        now = datetime.now().isoformat(timespec="seconds")
        with self._connection(write=True) as conn:
            conn.execute(
                """
                INSERT INTO ai_usage(user_id, usage_date, request_count, prompt_tokens, completion_tokens, last_request_at)
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(user_id, usage_date) DO UPDATE SET
                    request_count = request_count + 1,
                    prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                    completion_tokens = completion_tokens + excluded.completion_tokens,
                    last_request_at = excluded.last_request_at
                """,
                (str(user_id), day, max(0, int(prompt_tokens)), max(0, int(completion_tokens)), now),
            )

    def get_ai_global_stats(self) -> Dict[str, int]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(request_count),0), COALESCE(SUM(prompt_tokens),0), COALESCE(SUM(completion_tokens),0) FROM ai_usage"
            ).fetchone()
        return {"requests": int(row[0]), "prompt_tokens": int(row[1]), "completion_tokens": int(row[2])}

    def flatten_db(self) -> None:
        # Kept for migration-script compatibility. SQLite records are already flat.
        logger.info("SQLite hero schema is already flat; no migration required")


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _build_runtime_database():
    from app.config.settings import settings

    if settings.mongodb_configured:
        try:
            from app.db.mongo_database import MongoDatabase

            return MongoDatabase(
                settings.mongodb_url,
                db_name=settings.mongodb_db_name,
                timeout_ms=settings.mongodb_timeout_ms,
            )
        except Exception as exc:
            if settings.mongodb_required:
                raise RuntimeError("MongoDB is required but the connection failed") from exc
            logger.warning("MongoDB connection failed; falling back to SQLite: {}", type(exc).__name__)

    return Database()


db = _build_runtime_database()
