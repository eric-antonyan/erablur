"""One-time migration from the bundled SQLite database to MongoDB.

Usage:
    1. Put MONGODB_URL and MONGODB_DB_NAME in .env
    2. pip install -r requirements.txt
    3. python scripts/migrate_sqlite_to_mongo.py

The script upserts keyed collections and imports search history only when the
MongoDB history collection is empty, preventing accidental duplicate history.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.mongo_database import MongoDatabase  # noqa: E402


def fetch_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    try:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(row) for row in rows]


def main() -> None:
    if not settings.mongodb_url:
        raise SystemExit("MONGODB_URL is empty. Add your MongoDB connection string to .env first.")

    source = Path(settings.database_path)
    if not source.exists():
        raise SystemExit(f"SQLite database not found: {source}")

    mongo = MongoDatabase(settings.mongodb_url, settings.mongodb_db_name, settings.mongodb_timeout_ms)
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row

    counters: dict[str, int] = {}
    try:
        heroes = fetch_rows(conn, "heroes")
        for row in heroes:
            mongo.heroes.update_one({"id": str(row["id"])}, {"$set": row}, upsert=True)
        counters["heroes"] = len(heroes)

        users = fetch_rows(conn, "users")
        for row in users:
            row["id"] = str(row["id"])
            mongo.users.update_one({"id": row["id"]}, {"$set": row}, upsert=True)
        counters["users"] = len(users)

        channels = fetch_rows(conn, "channels")
        for row in channels:
            row["channel_id"] = int(row["channel_id"])
            row["owner_id"] = str(row["owner_id"])
            mongo.channels.update_one({"channel_id": row["channel_id"]}, {"$set": row}, upsert=True)
        counters["channels"] = len(channels)

        donations = fetch_rows(conn, "donations")
        for row in donations:
            row["order_id"] = str(row["order_id"])
            row["user_id"] = str(row["user_id"])
            mongo.donations.update_one({"order_id": row["order_id"]}, {"$set": row}, upsert=True)
        counters["donations"] = len(donations)

        ai_usage = fetch_rows(conn, "ai_usage")
        for row in ai_usage:
            row["user_id"] = str(row["user_id"])
            mongo.ai_usage.update_one(
                {"user_id": row["user_id"], "usage_date": row["usage_date"]},
                {"$set": row},
                upsert=True,
            )
        counters["ai_usage"] = len(ai_usage)

        history = fetch_rows(conn, "search_history")
        if mongo.search_history.count_documents({}) == 0 and history:
            for row in history:
                row.pop("id", None)
                row["user_id"] = str(row["user_id"])
            mongo.search_history.insert_many(history, ordered=False)
            counters["search_history"] = len(history)
        else:
            counters["search_history"] = 0
    finally:
        conn.close()
        mongo.close()

    print("Migration complete:")
    for name, count in counters.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
