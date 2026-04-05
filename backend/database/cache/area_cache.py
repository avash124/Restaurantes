from backend.database.cache.redis_client import get_json, set_json, delete_key

AREA_TTL_SECONDS = 60 * 30

async def get_cached_area(key: str):
    return await get_json(key)


async def set_cached_area(key: str, value: dict):
   
    await set_json(key, value, AREA_TTL_SECONDS)


async def invalidate_cached_area(key: str):
    await delete_key(key)