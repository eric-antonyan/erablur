from redis.asyncio import Redis
from app.config.settings import REDIS_HOST, REDIS_PORT, REDIS_PASS

cache: Redis = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    decode_responses=True,

    socket_timeout=3,
    socket_connect_timeout=3,
    retry_on_timeout=True,
    health_check_interval=30,
    max_connections=20,
)
