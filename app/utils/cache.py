from app.db.redis_db import cache
import json
from bson import ObjectId


def bson_to_json(data):
    """Recursively convert MongoDB BSON types (ObjectId, etc.) to JSON-serializable types."""
    if isinstance(data, dict):
        return {k: bson_to_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [bson_to_json(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    return data


def get_cached_hero(name: str):
    """Retrieve hero data from Redis by name."""
    cached = cache.get(f"hero:{name}")
    return json.loads(cached) if cached else None


def set_cached_hero(name: str, hero: dict):
    """Store hero data in Redis cache for 1 hour."""
    try:
        hero_json = json.dumps(bson_to_json(hero), ensure_ascii=False)
        cache.setex(f"hero:{name}", 3600, hero_json)
    except Exception as e:
        print(f"❌ Redis cache error for hero {name}: {e}")
