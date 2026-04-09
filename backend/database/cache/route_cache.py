from backend.database.cache.redis_client import get_json, set_json, delete_key

ROUTE_TTL_SECONDS = 60 * 60 * 24  


async def get_cached_route(key: str):
    return await get_json(key)


async def set_cached_route(key: str, value: dict):
    await set_json(key, value, ROUTE_TTL_SECONDS)


async def invalidate_cached_route(key: str):
    await delete_key(key)
