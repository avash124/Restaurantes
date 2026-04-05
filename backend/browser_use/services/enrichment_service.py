from backend.database.cache.cache_keys import restaurant_menu_key
from backend.database.cache.restaurant_cache import get_cached_restaurant_menu, set_cached_restaurant_menu
from backend.browser_use.agents.deep_analysis_agent import run_deep_restaurant_agent


async def enrich_restaurant(
    restaurant_name: str,
    website_url: str | None = None,
    location_hint: str | None = None,
):
    # restaurant_menu_key handles chain-normalisation internally; pass the raw name.
    key = restaurant_menu_key(restaurant_name)

    try:
        cached = await get_cached_restaurant_menu(key)
        if cached:
            return cached
    except Exception:
        pass  # Redis unavailable — skip cache read

    output = await run_deep_restaurant_agent(
        restaurant_name=restaurant_name,
        website_url=website_url,
        location_hint=location_hint,
    )

    payload = output.model_dump()

    try:
        await set_cached_restaurant_menu(key, payload)
    except Exception:
        pass  # Redis unavailable — skip cache write

    return payload