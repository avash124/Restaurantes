import asyncio

from backend.models.menu_item import MenuItemFacts
from backend.services.policy_service import _evaluate_rules_only, add_explanation_async


_VALID_EVIDENCE_SOURCE_TYPES = {
    "restaurant_explicit",
    "restaurant_inferred",
    "generic_recipe",
}

_EVIDENCE_SOURCE_TYPE_MAP = {
    "third_party_menu_aggregator": "restaurant_inferred",
}


def _normalize_evidence_source_type(raw_value: object) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return "restaurant_explicit"

    value = raw_value.strip()
    mapped = _EVIDENCE_SOURCE_TYPE_MAP.get(value, value)
    if mapped in _VALID_EVIDENCE_SOURCE_TYPES:
        return mapped

    return "restaurant_explicit"


def normalize_deep_menu_items(deep_output_dict: dict) -> list[MenuItemFacts]:
    items = []
    for item in deep_output_dict.get("menu_items", []):
        items.append(
            MenuItemFacts(
                name=item["name"],
                category=item.get("category"),
                description=item.get("description"),
                ingredients_explicit=item.get("ingredients_explicit", []),
                ingredients_inferred=item.get("ingredients_inferred", []),
                allergens_explicit=item.get("allergens_explicit", []),
                preparation_tags=item.get("preparation_tags", []),
                uncertainty_flags=item.get("uncertainty_flags", []),
                nutrition_explicit=item.get("nutrition_explicit", {}),
                evidence_source_type=_normalize_evidence_source_type(
                    item.get("evidence_source_type", "restaurant_explicit")
                ),
                extraction_confidence=item.get("extraction_confidence", 0.5),
            )
        )
    return items


_LABEL_RANK = {
    "Compatible": 0,
    "Caution": 1,
    "Unclear": 2,
    "High risk": 3,
}


async def rank_top_items_across_restaurants(
    enriched_restaurants: list[dict],
    condition_ids: list[str],
    top_n: int = 10,
) -> list[dict]:
    """
    1. Rule-evaluate ALL items across all restaurants (fast, no network).
    2. Sort and pick the global top_n candidates.
    3. Call Gemini explanations ONLY for those top_n items, concurrently.
    """
    # Phase 1: rule-based scoring for every item (no Gemini)
    all_candidates: list[tuple[dict, MenuItemFacts]] = []

    for restaurant in enriched_restaurants:
        menu_items = normalize_deep_menu_items(restaurant)
        for item in menu_items:
            try:
                _evaluate_rules_only(item, condition_ids)
            except Exception as exc:
                item.final_label = "Unclear"
                item.final_score = 0.0
                item.final_confidence = 0.05
                item.reasons = ["Unexpected evaluation failure"]
                item.missing_info = [str(exc)]

            all_candidates.append((restaurant, item))

    # Phase 2: sort by (label rank asc, confidence desc, score desc) and keep top_n
    all_candidates.sort(
        key=lambda x: (
            _LABEL_RANK.get(x[1].final_label, 99),
            -(x[1].final_confidence if x[1].final_confidence is not None else 0.0),
            -(x[1].final_score if x[1].final_score is not None else 0.0),
        )
    )
    top_candidates = all_candidates[:top_n]

    # Phase 3: add Gemini explanations only for the survivors, all at once
    await asyncio.gather(*[
        add_explanation_async(item, condition_ids)
        for _, item in top_candidates
    ])

    return [
        {
            "restaurant_name": restaurant["restaurant_name"],
            "restaurant_address": restaurant["address"],
            "item_name": item.name,
            "label": item.final_label,
            "score": item.final_score,
            "confidence": item.final_confidence,
            "short_explanation": item.short_explanation,
        }
        for restaurant, item in top_candidates
    ]
