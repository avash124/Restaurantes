def paginate_items(items: list[dict], offset: int = 0, limit: int = 10) -> dict:
    offset = max(0, offset)
    limit = max(1, min(limit, 100))

    sliced = items[offset:offset + limit]
    next_offset = offset + limit
    has_more = next_offset < len(items)

    return {
        "items": sliced,
        "total_count": len(items),
        "next_offset": next_offset if has_more else None,
        "has_more": has_more,
    }