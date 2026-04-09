import re


_KNOWN_CHAINS: frozenset[str] = frozenset({
    "mcdonalds", "burger king", "wendys", "taco bell", "chipotle",
    "subway", "chick fil a", "kfc", "pizza hut", "dominos", "papa johns",
    "five guys", "shake shack", "in n out", "panda express",
    "panera", "olive garden", "applebees", "ihop", "dennys",
    "outback steakhouse", "cheesecake factory", "red robin",
    "buffalo wild wings", "wingstop", "popeyes", "raising canes",
    "culvers", "sonic", "jack in the box", "carls jr", "del taco",
    "el pollo loco", "habit burger", "sweetgreen", "jersey mikes",
    "firehouse subs", "jimmy johns", "potbelly", "starbucks", "dunkin",
})


def _normalise(name: str) -> str:
    """Lowercase, strip punctuation/possessives, collapse whitespace."""
    n = name.lower()
    n = re.sub(r"[''`]s?\b", "", n)   
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def chain_slug(restaurant_name: str) -> str | None:
    """
    Return a stable slug for well-known chains, or None for independents.

    The slug is shared across all locations of the same chain, so their menu
    snapshots merge into one cache entry.
    """
    normalised = _normalise(restaurant_name)
    for chain in _KNOWN_CHAINS:
        if chain in normalised or normalised in chain:
            return chain.replace(" ", "_")
    return None


def area_key(
    lat_bucket: str,
    lng_bucket: str,
    radius_miles: float,
    category: str | None = None,
) -> str:
    """
    Cache key for restaurant discovery in an area.

    Category is intentionally ignored so semantically equivalent queries in the
    same location/radius can reuse the same wide-discovery cache entry.
    """
    _ = category
    radius_bucket = f"{float(radius_miles):.2f}"
    return f"area:{lat_bucket}:{lng_bucket}:{radius_bucket}"


def restaurant_menu_key(restaurant_name: str) -> str:
    """
    Cache key for a restaurant's menu snapshot.

    Well-known chains get a location-independent key so every branch shares the
    same cached menu.  Independent restaurants get a per-name key.
    """
    slug = chain_slug(restaurant_name)
    if slug:
        return f"chain:{slug}:menu_snapshot"
    safe = restaurant_name.lower().replace(" ", "_")
    return f"restaurant:{safe}:menu_snapshot"


def route_key(origin_hash: str, restaurant_id: str, travel_mode: str) -> str:
    return f"route:{origin_hash}:{restaurant_id}:{travel_mode}"


def job_progress_key(job_id: str) -> str:
    return f"job:{job_id}:progress"
