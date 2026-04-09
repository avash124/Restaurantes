import asyncio
import hashlib
from typing import List

from backend.models.menu_item import MenuItemFacts
from backend.models.eval import ConditionEvaluation
from backend.engine.dispatch import evaluate_item_for_condition
from backend.engine.aggregator import aggregate_condition_results
from backend.engine.explaination import confidence_band, generate_short_explanation
from backend.gemini_llm.gemini_explainations import generate_short_explanation_with_gemini_async

# In-memory cache: avoids re-calling Gemini for items with identical label/reasons/ingredients
_explanation_cache: dict[str, str] = {}

# Max concurrent Gemini explanation calls at once
_EXPLANATION_SEM = asyncio.Semaphore(5)


def _explanation_cache_key(
    label: str,
    band: str,
    reasons: list[str],
    missing_info: list[str],
    ingredients: list[str],
    condition_ids: list[str],
) -> str:
    parts = (
        label,
        band,
        tuple(sorted(reasons[:2])),
        tuple(sorted(missing_info[:1])),
        tuple(sorted(ingredients[:3])),
        tuple(sorted(condition_ids)),
    )
    return hashlib.md5(str(parts).encode()).hexdigest()


def _evaluate_rules_only(
    item: MenuItemFacts,
    condition_ids: List[str],
) -> MenuItemFacts:
    """Phase 1: run the rule-based policy engine only. Fast, no network calls."""
    per_condition: List[ConditionEvaluation] = []

    for condition_id in condition_ids:
        try:
            result = evaluate_item_for_condition(item, condition_id)
        except Exception as exc:
            result = ConditionEvaluation(
                condition_id=condition_id,
                label="Unclear",
                score=0,
                confidence=0.05,
                reasons=[f"Evaluation error for '{condition_id}'"],
                missing_info=[str(exc)],
            )
        per_condition.append(result)

    combined = aggregate_condition_results(per_condition)

    item.per_condition_results = per_condition
    item.final_label = combined.label
    item.final_score = combined.score
    item.final_confidence = combined.confidence
    item.reasons = combined.reasons
    item.missing_info = combined.missing_info
    return item


async def add_explanation_async(item: MenuItemFacts, condition_ids: List[str]) -> MenuItemFacts:
    """Phase 2: generate a Gemini explanation for a rule-evaluated item. Cached + concurrent."""
    all_ingredients = list(dict.fromkeys(item.ingredients_explicit + item.ingredients_inferred))
    band = confidence_band(item.final_confidence)

    cache_key = _explanation_cache_key(
        item.final_label, band, item.reasons, item.missing_info,
        all_ingredients, condition_ids,
    )

    if cache_key in _explanation_cache:
        item.short_explanation = _explanation_cache[cache_key]
        return item

    try:
        async with _EXPLANATION_SEM:
            explanation = await generate_short_explanation_with_gemini_async(
                item_name=item.name,
                label=item.final_label,
                confidence_band=band,
                reasons=item.reasons,
                missing_info=item.missing_info,
                ingredients=all_ingredients or None,
                condition_ids=condition_ids,
            )
        _explanation_cache[cache_key] = explanation
        item.short_explanation = explanation
    except Exception:
        item.short_explanation = generate_short_explanation(
            label=item.final_label,
            reasons=item.reasons,
            missing_info=item.missing_info,
            confidence=item.final_confidence,
        )

    return item


async def evaluate_menu_items_for_conditions(
    menu_items: List[MenuItemFacts],
    condition_ids: List[str],
) -> List[MenuItemFacts]:
    # Phase 1: rule-based evaluation for all items (fast, synchronous)
    evaluated: List[MenuItemFacts] = []
    for item in menu_items:
        try:
            evaluated.append(_evaluate_rules_only(item, condition_ids))
        except Exception as exc:
            item.final_label = "Unclear"
            item.final_score = 0.0
            item.final_confidence = 0.05
            item.reasons = ["Unexpected evaluation failure"]
            item.missing_info = [str(exc)]
            item.short_explanation = (
                "Safety is uncertain for this item. "
                "Confidence is low because an unexpected error occurred during evaluation. "
                "Ask restaurant staff for a full ingredient list before ordering."
            )
            evaluated.append(item)

    # Phase 2: add Gemini explanations concurrently
    await asyncio.gather(*[add_explanation_async(item, condition_ids) for item in evaluated])

    return evaluated
