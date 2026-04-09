import logging

from backend.database.cache.cache_keys import restaurant_menu_key
from backend.database.cache.restaurant_cache import get_cached_restaurant_menu, set_cached_restaurant_menu
from backend.browser_use.agents.deep_analysis_agent import run_deep_restaurant_agent

logger = logging.getLogger(__name__)


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
    except Exception as exc:
        logger.warning("[enrich] cache read failed for %s: %s", restaurant_name, exc)

    # Wrap deep analysis so an unexpected exception never prevents the cache
    # write below from running and never silently swallows error context.
    try:
        output = await run_deep_restaurant_agent(
            restaurant_name=restaurant_name,
            website_url=website_url,
            location_hint=location_hint,
        )
    except Exception as exc:
        logger.warning("[enrich] deep analysis failed for %s: %s", restaurant_name, exc)
        return {
            "restaurant_name": restaurant_name,
            "address": "",
            "website_url": website_url,
            "menu_items": [],
        }

    payload = output.model_dump()

    try:
        await set_cached_restaurant_menu(key, payload)
    except Exception as exc:
        logger.warning("[enrich] cache write failed for %s: %s", restaurant_name, exc)

    return payload