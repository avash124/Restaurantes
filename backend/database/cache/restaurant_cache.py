from backend.database.cache.redis_client import get_json, set_json, delete_key

RESTAURANT_MENU_TTL_SECONDS = 60 * 60 * 12  # 12 hours


async def get_cached_restaurant_menu(key: str):
    return await get_json(key)


async def set_cached_restaurant_menu(key: str, value: dict):
    await set_json(key, value, RESTAURANT_MENU_TTL_SECONDS)


async def invalidate_cached_restaurant_menu(key: str):
    await delete_key(key)