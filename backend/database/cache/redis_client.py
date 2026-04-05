import json
import asyncio
import time
import redis.asyncio as redis

from backend.database.core.config import settings

redis_client = redis.from_url(settings.redis_cache_url, decode_responses=True)

# In-memory fallback cache used when Redis is unavailable.
_fallback_cache: dict[str, tuple[float | None, dict]] = {}
_fallback_lock = asyncio.Lock()
_REDIS_RETRY_COOLDOWN_SECONDS = 30.0
_redis_disabled_until = 0.0


def _redis_temporarily_disabled() -> bool:
    return time.monotonic() < _redis_disabled_until


def _mark_redis_failure() -> None:
    global _redis_disabled_until
    _redis_disabled_until = time.monotonic() + _REDIS_RETRY_COOLDOWN_SECONDS


async def _fallback_get(key: str):
    now = time.monotonic()
    async with _fallback_lock:
        entry = _fallback_cache.get(key)
        if not entry:
            return None

        expires_at, value = entry
        if expires_at is not None and expires_at <= now:
            _fallback_cache.pop(key, None)
            return None

        return value


async def _fallback_set(key: str, value: dict, ttl_seconds: int):
    expires_at = time.monotonic() + max(ttl_seconds, 1)
    safe_value = json.loads(json.dumps(value))  # defensive copy
    async with _fallback_lock:
        _fallback_cache[key] = (expires_at, safe_value)


async def _fallback_delete(key: str):
    async with _fallback_lock:
        _fallback_cache.pop(key, None)


async def get_json(key: str):
    if not _redis_temporarily_disabled():
        try:
            raw = await redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            _mark_redis_failure()

    return await _fallback_get(key)


async def set_json(key: str, value: dict, ttl_seconds: int):
    if not _redis_temporarily_disabled():
        try:
            await redis_client.setex(key, ttl_seconds, json.dumps(value))
        except Exception:
            _mark_redis_failure()

    await _fallback_set(key, value, ttl_seconds)


async def delete_key(key: str):
    if not _redis_temporarily_disabled():
        try:
            await redis_client.delete(key)
        except Exception:
            _mark_redis_failure()

    await _fallback_delete(key)
