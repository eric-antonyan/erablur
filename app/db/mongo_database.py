"""MongoDB data backend matching the synchronous database interface used by handlers.

The bot's handlers are synchronous at the data-access boundary, so PyMongo is
used here instead of Motor to avoid a project-wide async refactor.  MongoDB is
selected only when ``MONGODB_URL`` is configured; otherwise the existing
SQLite backend remains available as a safe fallback.
"""
from __future__ import annotations

import random
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as PyMongoDatabase

from app.utils.armenian_search import (
    QUESTION_STOPWORDS,
    armenian_tokens,
    hero_display_name,
    normalize_armenian_text,
    rank_hero_name_candidates,
)


class MongoDatabase:
    def __init__(self, url: str, db_name: str = "erablur", timeout_ms: int = 5000):
        self.client = MongoClient(
            url,
            serverSelectionTimeoutMS=int(timeout_ms),
            connectTimeoutMS=int(timeout_ms),
            socketTimeoutMS=max(int(timeout_ms), 5000),
            retryWrites=True,
        )
        # Fail fast so startup can decide whether to fall back to SQLite.
        self.client.admin.command("ping")
        self.db: PyMongoDatabase = self.client[db_name]
        self.heroes: Collection = self.db["heroes"]
        self.users: Collection = self.db["users"]
        self.search_history: Collection = self.db["search_history"]
        self.channels: Collection = self.db["channels"]
        self.donations: Collection = self.db["donations"]
        self.ai_usage: Collection = self.db["ai_usage"]
        self._init_indexes()
        logger.info("MongoDB connected and indexes are ready | database={}", db_name)

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _clean(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if doc is None:
            return None
        result = dict(doc)
        result.pop("_id", None)
        return result

    @classmethod
    def _clean_many(cls, docs) -> List[Dict[str, Any]]:
        return [cls._clean(doc) for doc in docs if doc is not None]

    def _init_indexes(self) -> None:
        self.heroes.create_index([("id", ASCENDING)], unique=True, name="heroes_id_unique")
        self.heroes.create_index([("first_name", ASCENDING), ("last_name", ASCENDING)], name="heroes_name")
        self.heroes.create_index([("war", ASCENDING)], name="heroes_war")
        self.heroes.create_index([("region", ASCENDING)], name="heroes_region")

        self.users.create_index([("id", ASCENDING)], unique=True, name="users_id_unique")
        self.users.create_index([("username", ASCENDING)], name="users_username")
        self.users.create_index([("search_count", DESCENDING)], name="users_search_count")
        self.users.create_index([("updated_at", DESCENDING)], name="users_updated_at")

        self.search_history.create_index([("user_id", ASCENDING), ("searched_at", DESCENDING)], name="history_user_date")
        self.search_history.create_index([("query", ASCENDING)], name="history_query")

        self.channels.create_index([("channel_id", ASCENDING)], unique=True, name="channels_id_unique")
        self.channels.create_index([("owner_id", ASCENDING), ("connected_at", DESCENDING)], name="channels_owner")

        self.donations.create_index([("order_id", ASCENDING)], unique=True, name="donations_order_unique")
        self.donations.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="donations_user")
        self.donations.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="donations_status")

        self.ai_usage.create_index([("user_id", ASCENDING), ("usage_date", ASCENDING)], unique=True, name="ai_usage_user_day")

    def ping(self) -> bool:
        try:
            return bool(self.client.admin.command("ping").get("ok"))
        except Exception:
            return False

    # Heroes -----------------------------------------------------------------
    def save_hero(self, hero_id: str, data: Dict[str, Any]) -> None:
        nested_name = data.get("name") if isinstance(data.get("name"), dict) else {}
        nested_date = data.get("date") if isinstance(data.get("date"), dict) else {}
        now = self._now()
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
            "updated_at": now,
        }
        self.heroes.update_one(
            {"id": str(hero_id)},
            {"$set": payload, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    def get_hero(self, hero_id: str) -> Optional[Dict[str, Any]]:
        return self._clean(self.heroes.find_one({"id": str(hero_id)}))

    def delete_hero(self, hero_id: str) -> bool:
        return self.heroes.delete_one({"id": str(hero_id)}).deleted_count > 0

    def get_heroes_by_name(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
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
            best_name = normalize_armenian_text(hero_display_name(ranked[0][1]))
            return [
                hero for score, hero in ranked
                if score >= 900.0 and normalize_armenian_text(hero_display_name(hero)) == best_name
            ][:limit]
        else:
            threshold = max(760.0, best - 35.0)
        return [hero for score, hero in ranked if score >= threshold][:limit]

    def get_heroes_by_names(self, first_name: str, last_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_heroes_by_name(f"{first_name} {last_name}", limit=limit)

    def search_heroes_for_context(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        normalized = normalize_armenian_text(query)
        if not normalized:
            return []
        limit = max(1, min(int(limit), 12))
        heroes = self.get_all_heroes()

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
                points += matched * 3.0
                scored.append((points, hero))

        scored.sort(
            key=lambda item: (
                -item[0],
                normalize_armenian_text(hero_display_name(item[1])),
                str(item[1].get("id", "")),
            )
        )
        return [hero for _, hero in scored[:limit]]

    def get_heroes_by_war(self, war: str) -> List[Dict[str, Any]]:
        return self._clean_many(self.heroes.find({"war": war}).sort([("first_name", ASCENDING), ("last_name", ASCENDING)]))

    def get_all_heroes(self) -> List[Dict[str, Any]]:
        return self._clean_many(self.heroes.find({}).sort([("first_name", ASCENDING), ("last_name", ASCENDING)]))

    def get_random_heroes(self, limit: int = 6) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 20))
        try:
            return self._clean_many(self.heroes.aggregate([{"$sample": {"size": limit}}]))
        except Exception:
            heroes = self.get_all_heroes()
            random.shuffle(heroes)
            return heroes[:limit]

    def count_heroes(self) -> int:
        return int(self.heroes.count_documents({}))

    def get_all_wars(self) -> List[str]:
        wars = [str(value).strip() for value in self.heroes.distinct("war") if str(value or "").strip()]
        return sorted(set(wars), key=str.casefold)

    # Users and history -------------------------------------------------------
    def save_user(self, user_id: str, username: str, first_name: str, last_name: str = "") -> None:
        now = self._now()
        self.users.update_one(
            {"id": str(user_id)},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "updated_at": now,
                },
                "$setOnInsert": {"id": str(user_id), "search_count": 0, "joined_at": now},
            },
            upsert=True,
        )

    def get_user(self, user_id: str | int) -> Optional[Dict[str, Any]]:
        return self._clean(self.users.find_one({"id": str(user_id)}))

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        username = username.strip().lstrip("@")
        if not username:
            return None
        return self._clean(self.users.find_one({"username": {"$regex": f"^{self._regex_escape(username)}$", "$options": "i"}}))

    @staticmethod
    def _regex_escape(value: str) -> str:
        import re
        return re.escape(value)

    def get_all_users(self, limit: int | None = None) -> List[Dict[str, Any]]:
        cursor = self.users.find({}).sort("updated_at", DESCENDING)
        if limit is not None:
            cursor = cursor.limit(max(1, min(int(limit), 100000)))
        return self._clean_many(cursor)

    def increment_search_count(self, user_id: str, query: str) -> None:
        self.users.update_one(
            {"id": str(user_id)},
            {"$inc": {"search_count": 1}, "$set": {"last_query": query, "updated_at": self._now()}},
        )

    def add_search_history(self, user_id: str, query: str, hero_id: str, hero_name: str) -> None:
        self.search_history.insert_one(
            {
                "user_id": str(user_id),
                "query": query,
                "hero_id": str(hero_id),
                "hero_name": hero_name,
                "searched_at": self._now(),
            }
        )

    def get_user_search_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        return self._clean_many(self.search_history.find({"user_id": str(user_id)}).sort("searched_at", DESCENDING).limit(limit))

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.get_user_search_history(user_id, limit)

    def clear_user_history(self, user_id: str) -> int:
        return int(self.search_history.delete_many({"user_id": str(user_id)}).deleted_count)

    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        pipeline = [
            {"$group": {"_id": "$query", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "query": "$_id", "count": 1}},
        ]
        return [dict(row) for row in self.search_history.aggregate(pipeline)]

    def get_global_stats(self) -> Dict[str, Any]:
        total_users = int(self.users.count_documents({}))
        total_heroes = int(self.heroes.count_documents({}))
        totals = list(self.users.aggregate([{"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$search_count", 0]}}}}]))
        total_searches = int(totals[0]["total"]) if totals else 0
        top_users = self._clean_many(self.users.find({}).sort([("search_count", DESCENDING), ("updated_at", DESCENDING)]).limit(5))
        last_user = self._clean(self.users.find_one({}, sort=[("updated_at", DESCENDING)]))
        return {
            "total_users": total_users,
            "total_searches": total_searches,
            "total_heroes": total_heroes,
            "last_user": last_user,
            "top_users": top_users,
        }

    # Channels ---------------------------------------------------------------
    def save_channel(self, channel_id: int, title: str, owner_id: str) -> None:
        now = self._now()
        self.channels.update_one(
            {"channel_id": int(channel_id)},
            {"$set": {"channel_id": int(channel_id), "title": title, "owner_id": str(owner_id), "connected_at": now}},
            upsert=True,
        )

    @staticmethod
    def _channel_compat(row: Dict[str, Any]) -> Dict[str, Any]:
        row["id"] = row.get("channel_id")
        return row

    def get_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        row = self._clean(self.channels.find_one({"channel_id": int(channel_id)}))
        return self._channel_compat(row) if row else None

    def get_user_channels(self, owner_id: str) -> List[Dict[str, Any]]:
        rows = self._clean_many(self.channels.find({"owner_id": str(owner_id)}).sort("connected_at", DESCENDING))
        return [self._channel_compat(row) for row in rows]

    def get_all_channels(self) -> List[Dict[str, Any]]:
        rows = self._clean_many(self.channels.find({}).sort("connected_at", DESCENDING))
        return [self._channel_compat(row) for row in rows]

    def delete_channel(self, channel_id: int) -> bool:
        return self.channels.delete_one({"channel_id": int(channel_id)}).deleted_count > 0

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
        now = self._now()
        existing = self.donations.find_one({"order_id": str(order_id)}, {"provider_payment_id": 1, "invoice_url": 1}) or {}
        self.donations.update_one(
            {"order_id": str(order_id)},
            {
                "$set": {
                    "user_id": str(user_id),
                    "provider": provider,
                    "amount": str(amount),
                    "currency": currency,
                    "status": status,
                    "anonymous": 1 if anonymous else 0,
                    "provider_payment_id": provider_payment_id or existing.get("provider_payment_id", ""),
                    "invoice_url": invoice_url or existing.get("invoice_url", ""),
                    "updated_at": now,
                },
                "$setOnInsert": {"order_id": str(order_id), "created_at": now},
            },
            upsert=True,
        )

    def get_donation(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._clean(self.donations.find_one({"order_id": str(order_id)}))

    def get_user_donations(self, user_id: str | int, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        return self._clean_many(self.donations.find({"user_id": str(user_id)}).sort("created_at", DESCENDING).limit(limit))

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
        existing = self.donations.find_one({"order_id": str(order_id)})
        if not existing:
            return False
        now = self._now()
        fields: Dict[str, Any] = {"status": status, "updated_at": now}
        optional = {
            "provider_payment_id": provider_payment_id,
            "telegram_charge_id": telegram_charge_id,
            "invoice_url": invoice_url,
            "paid_amount": paid_amount,
            "paid_currency": paid_currency,
            "network": network,
            "txid": txid,
        }
        fields.update({key: value for key, value in optional.items() if value != ""})
        if mark_paid and not existing.get("paid_at"):
            fields["paid_at"] = now
        result = self.donations.update_one({"order_id": str(order_id)}, {"$set": fields})
        return result.matched_count > 0

    def mark_donation_notified(self, order_id: str) -> None:
        existing = self.donations.find_one({"order_id": str(order_id)}, {"notified_at": 1})
        if not existing:
            return
        now = self._now()
        fields = {"updated_at": now}
        if not existing.get("notified_at"):
            fields["notified_at"] = now
        self.donations.update_one({"order_id": str(order_id)}, {"$set": fields})

    def get_donation_stats(self) -> Dict[str, Any]:
        docs = self._clean_many(self.donations.find({}).sort("created_at", DESCENDING))
        paid_statuses = {"paid", "paid_over", "completed"}
        total_orders = len(docs)
        paid_orders = sum(1 for row in docs if row.get("status") in paid_statuses)
        stars_total = 0.0
        crypto_total = 0.0
        for row in docs:
            try:
                amount = float(row.get("amount") or 0)
            except (TypeError, ValueError):
                amount = 0.0
            if row.get("provider") == "telegram_stars" and row.get("status") == "completed":
                stars_total += amount
            if row.get("provider") == "cryptomus" and row.get("status") in {"paid", "paid_over"}:
                crypto_total += amount
        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "stars_total": stars_total,
            "crypto_total": crypto_total,
            "recent": docs[:15],
        }

    # AI usage ---------------------------------------------------------------
    def get_ai_usage_count(self, user_id: str | int, usage_date: date | None = None) -> int:
        day = (usage_date or date.today()).isoformat()
        row = self.ai_usage.find_one({"user_id": str(user_id), "usage_date": day}, {"request_count": 1})
        return int((row or {}).get("request_count", 0))

    def record_ai_usage(
        self,
        user_id: str | int,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        usage_date: date | None = None,
    ) -> None:
        day = (usage_date or date.today()).isoformat()
        self.ai_usage.update_one(
            {"user_id": str(user_id), "usage_date": day},
            {
                "$inc": {
                    "request_count": 1,
                    "prompt_tokens": max(0, int(prompt_tokens)),
                    "completion_tokens": max(0, int(completion_tokens)),
                },
                "$set": {"last_request_at": self._now()},
                "$setOnInsert": {"user_id": str(user_id), "usage_date": day},
            },
            upsert=True,
        )

    def get_ai_global_stats(self) -> Dict[str, int]:
        rows = list(
            self.ai_usage.aggregate(
                [
                    {
                        "$group": {
                            "_id": None,
                            "requests": {"$sum": {"$ifNull": ["$request_count", 0]}},
                            "prompt_tokens": {"$sum": {"$ifNull": ["$prompt_tokens", 0]}},
                            "completion_tokens": {"$sum": {"$ifNull": ["$completion_tokens", 0]}},
                        }
                    }
                ]
            )
        )
        if not rows:
            return {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0}
        row = rows[0]
        return {
            "requests": int(row.get("requests", 0)),
            "prompt_tokens": int(row.get("prompt_tokens", 0)),
            "completion_tokens": int(row.get("completion_tokens", 0)),
        }

    def flatten_db(self) -> None:
        # New writes are flat. This method is kept for compatibility with the
        # project's migration script and can normalize older nested documents.
        changed = 0
        for hero in self.heroes.find({}):
            nested_name = hero.get("name") if isinstance(hero.get("name"), dict) else {}
            nested_date = hero.get("date") if isinstance(hero.get("date"), dict) else {}
            updates: Dict[str, Any] = {}
            if "first_name" not in hero and nested_name:
                updates["first_name"] = str(nested_name.get("first", "") or "").strip()
            if "last_name" not in hero and nested_name:
                updates["last_name"] = str(nested_name.get("last", "") or "").strip()
            if "birth_date" not in hero and nested_date:
                updates["birth_date"] = str(nested_date.get("birth", "") or "").strip()
            if "death_date" not in hero and nested_date:
                updates["death_date"] = str(nested_date.get("dead", "") or "").strip()
            if updates:
                updates["updated_at"] = self._now()
                self.heroes.update_one({"_id": hero["_id"]}, {"$set": updates})
                changed += 1
        logger.info("MongoDB hero flatten migration complete | updated={}", changed)

    def close(self) -> None:
        self.client.close()
