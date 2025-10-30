import redis
from app.config.settings import REDIS_HOST, REDIS_PORT, REDIS_PASS

cache = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    decode_responses=True
)
