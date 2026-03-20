from upstash_redis import Redis
from functools import lru_cache
from .config import settings

@lru_cache
def get_redis():
    return Redis(url=settings.REDIS_URL, token=settings.REDIS_TOKEN)

