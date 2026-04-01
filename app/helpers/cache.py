import hashlib
from app.redis import get_redis
import json

CACHE_TTL_SECONDS = 3600
redis = get_redis()


def create_key(tenant_id: str, model: str, message: str, max_tokens: int, temperature: float) -> str:
    payload = {
        "model": model.lower(),
        "message": message.strip(),
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    canonical_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return f"v1:cache:{tenant_id}:{hashlib.sha256(canonical_string.encode()).hexdigest()}"


def get_cache(key: str):
    data =  redis.get(key)
    if data:
        return json.loads(data)
    return None

def set_cache(key: str, value: str):
    redis.set(key, json.dumps(value), ex=CACHE_TTL_SECONDS)




