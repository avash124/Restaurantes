from backend.models.menu_item import MenuItemFacts
from backend.services.policy_service import evaluate_menu_items_for_conditions


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


def rank_top_items_across_restaurants(
    enriched_restaurants: list[dict],
    condition_ids: list[str],
    top_n: int = 10,
):
    ranked_items = []

    for restaurant in enriched_restaurants:
        menu_items = normalize_deep_menu_items(restaurant)
        evaluated_items = evaluate_menu_items_for_conditions(menu_items, condition_ids)

        for item in evaluated_items:
            ranked_items.append(
                {
                    "restaurant_name": restaurant["restaurant_name"],
                    "restaurant_address": restaurant["address"],
                    "item_name": item.name,
                    "label": item.final_label,
                    "score": item.final_score,
                    "confidence": item.final_confidence,
                    "short_explanation": item.short_explanation,
                }
            )

    label_rank = {
        "Compatible": 0,
        "Caution": 1,
        "Unclear": 2,
        "High risk": 3,
    }

    ranked_items.sort(
        key=lambda x: (
            label_rank.get(x["label"], 99),
            -(x["confidence"] if x["confidence"] is not None else 0.0),
            -(x["score"] if x["score"] is not None else 0.0),
        )
    )

    return ranked_items[:top_n]
