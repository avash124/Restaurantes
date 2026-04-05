"""
Pre-warm menu cache for well-known fast-food and chain restaurants.

The scheduled Celery task calls warm_hot_chains() which runs deep analysis on
each chain and writes the result to Redis.  Subsequent requests for these
restaurants are cache hits — no browser-use or Playwright needed at request time.
"""

from __future__ import annotations

import asyncio
import logging

from backend.browser_use.services.enrichment_service import enrich_restaurant

logger = logging.getLogger(__name__)

# (display name, known homepage URL)
HOT_CHAINS: list[tuple[str, str]] = [
    ("McDonald's",           "https://www.mcdonalds.com/us/en-us/full_menu.html"),
    ("Burger King",          "https://www.bk.com/menu"),
    ("Taco Bell",            "https://www.tacobell.com/food"),
    ("Chipotle",             "https://www.chipotle.com/menu"),
    ("Subway",               "https://www.subway.com/en-US/MenuNutrition/Menu"),
    ("Chick-fil-A",          "https://www.chick-fil-a.com/menu"),
    ("KFC",                  "https://www.kfc.com/menu"),
    ("Wendy's",              "https://www.wendys.com/menu"),
    ("Pizza Hut",            "https://www.pizzahut.com/menu"),
    ("Domino's",             "https://www.dominos.com/en/pages/order/"),
    ("Panda Express",        "https://www.pandaexpress.com/menu"),
    ("Panera Bread",         "https://www.panerabread.com/en-us/menu.html"),
    ("Five Guys",            "https://www.fiveguys.com/menu"),
    ("Shake Shack",          "https://www.shakeshack.com/menu/"),
    ("Sweetgreen",           "https://www.sweetgreen.com/menu"),
    ("Wingstop",             "https://www.wingstop.com/menu"),
    ("Popeyes",              "https://www.popeyes.com/menu"),
    ("Jack in the Box",      "https://www.jackinthebox.com/menu"),
    ("Sonic",                "https://www.sonicdrivein.com/menu"),
    ("In-N-Out Burger",      "https://www.in-n-out.com/menu"),
]


async def warm_one_chain(name: str, url: str) -> bool:
    """
    Ensure *name* is in the menu cache.  Returns True if already cached or
    successfully warmed, False on failure.
    """
    try:
        result = await enrich_restaurant(
            restaurant_name=name,
            website_url=url,
            location_hint=None,
        )
        items = len(result.get("menu_items", []))
        logger.info("[warmup] %s — %d items cached", name, items)
        return True
    except Exception as exc:
        logger.warning("[warmup] failed for %s: %s", name, exc)
        return False


async def warm_hot_chains() -> dict[str, bool]:
    """
    Warm all HOT_CHAINS concurrently (capped at 4 in flight at once to avoid
    hammering browser-use quota).  Returns a {name: success} mapping.
    """
    semaphore = asyncio.Semaphore(4)

    async def _guarded(name: str, url: str) -> tuple[str, bool]:
        async with semaphore:
            ok = await warm_one_chain(name, url)
            return name, ok

    results = await asyncio.gather(
        *[_guarded(name, url) for name, url in HOT_CHAINS],
        return_exceptions=False,
    )
    return dict(results)
