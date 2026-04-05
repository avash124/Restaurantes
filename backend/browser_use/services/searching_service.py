from backend.browser_use.agents.wide_browsing_agent import run_wide_discovery_agent
from backend.database.cache.cache_keys import area_key
from backend.database.cache.area_cache import get_cached_area, set_cached_area


async def discover_restaurants_for_query(
    lat_bucket: str,
    lng_bucket: str,
    location: str,
    radius_miles: float,
    category: str,
):
    key = area_key(lat_bucket, lng_bucket, radius_miles, category)

    try:
        cached = await get_cached_area(key)
        if cached:
            return cached
    except Exception:
        pass  # Redis unavailable — skip cache read

    output = await run_wide_discovery_agent(location, radius_miles, category)
    payload = {"restaurants": [r.model_dump() for r in output.restaurants]}

    try:
        await set_cached_area(key, payload)
    except Exception:
        pass  # Redis unavailable — skip cache write

    return payload