from .redis_keys import RedisKeys
from ..redis import get_redis
import time
redis = get_redis()

def check_rpm_token_bucket(key: str, limit: int):
    now = time.time()
    refill_rate = limit / 60
    last = float(redis.get(f"{key}:last") or now)
    token = float(redis.get(f"{key}:token") or limit)
    elapsed = now - last
    token = min(limit, token + elapsed*refill_rate)
    if token < 1:
        return False
    redis.set(f"{key}:token", token - 1)
    redis.set(f"{key}:last", now)
    return True

def check_tpm(key: str, limit: int, token: int):
    current = redis.incrby(key, token)
    if current == token:
        redis.expire(key, 60)
    return current <= limit

def concurrency_acquire(key: str, limit: int):
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, 60)
    if current > limit:
        redis.decr(key)
        return False
    return True

def release_concurrency(key: str):
    redis.decr(key)