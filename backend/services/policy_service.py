from typing import List

from backend.models.menu_item import MenuItemFacts
from backend.models.eval import ConditionEvaluation
from backend.engine.dispatch import evaluate_item_for_condition
from backend.engine.aggregator import aggregate_condition_results
from backend.engine.explaination import confidence_band
from backend.gemini_llm.gemini_explainations import generate_short_explanation_with_gemini


def evaluate_single_item(
    item: MenuItemFacts,
    condition_ids: List[str],
) -> MenuItemFacts:
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
    all_ingredients = list(dict.fromkeys(item.ingredients_explicit + item.ingredients_inferred))
    try:
        item.short_explanation = generate_short_explanation_with_gemini(
            item_name=item.name,
            label=combined.label,
            confidence_band=confidence_band(combined.confidence),
            reasons=combined.reasons,
            missing_info=combined.missing_info,
            ingredients=all_ingredients or None,
            condition_ids=condition_ids,
        )
    except Exception:
        from backend.engine.explaination import generate_short_explanation
        item.short_explanation = generate_short_explanation(
            label=combined.label,
            reasons=combined.reasons,
            missing_info=combined.missing_info,
            confidence=combined.confidence,
        )

    return item


def evaluate_menu_items_for_conditions(
    menu_items: List[MenuItemFacts],
    condition_ids: List[str],
) -> List[MenuItemFacts]:
 
    evaluated: List[MenuItemFacts] = []

    for item in menu_items:
        try:
            evaluated.append(evaluate_single_item(item, condition_ids))
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

    return evaluated
