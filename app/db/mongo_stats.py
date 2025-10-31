from datetime import datetime
from app.db.mongo import users_collection

def increment_user_search(user: dict, query: str):
    """Increment user's search counter."""
    update = {
        "$inc": {"search_count": 1},
        "$set": {
            "first_name": user.first_name,
            "username": user.username,
            "last_query": query,
            "updated_at": datetime.utcnow()
        },
        "$setOnInsert": {"created_at": datetime.utcnow()}
    }
    users_collection.update_one({"id": str(user.id)}, update, upsert=True)
    print("updated")


async def get_user_stats(user_id: int):
    """Return one user's stats."""
    return await users_collection.find_one({"_id": user_id})


async def get_global_stats():
    """Return total users, total searches, and latest active user."""
    total_users = await users_collection.count_documents({})
    pipeline = [{"$group": {"_id": None, "total_searches": {"$sum": "$search_count"}}}]
    agg = [a async for a in users_collection.aggregate(pipeline)]
    total_searches = agg[0]["total_searches"] if agg else 0
    last_user = await users_collection.find_one(sort=[("updated_at", -1)])
    return total_users, total_searches, last_user
