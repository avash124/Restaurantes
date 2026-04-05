from backend.models.menu_item import MenuItemFacts
from backend.models.condition_policy import ConditionPolicy
from backend.models.eval import ConditionEvaluation
from backend.engine.confidence import compute_confidence


def _ingredient_matches(query: str, ingredient_set: set[str]) -> bool:
    """Substring match in either direction: 'peanut' matches 'peanut butter', and vice versa."""
    q = query.lower()
    for ing in ingredient_set:
        if q in ing or ing in q:
            return True
    return False


def evaluate_condition(item: MenuItemFacts, policy: ConditionPolicy) -> ConditionEvaluation:
    reasons = []
    missing_info = []
    matched_rules = []
    score = 100.0
    confidence = compute_confidence(item)

    explicit_ingredients = {x.lower() for x in item.ingredients_explicit}
    inferred_ingredients = {x.lower() for x in item.ingredients_inferred}
    allergens = {x.lower() for x in item.allergens_explicit}
    tags = {x.lower() for x in item.preparation_tags}

    
    for ing in policy.blocked_ingredients:
        if _ingredient_matches(ing, explicit_ingredients):
            return ConditionEvaluation(
                condition_id=policy.condition_id,
                label="High risk",
                score=5,
                confidence=min(1.0, confidence + 0.15),
                reasons=[f"Explicitly contains {ing}"],
                matched_rules=[f"blocked_ingredient:{ing}"],
            )

   
    for allergen in policy.blocked_allergens:
        if allergen.lower() in allergens:
            return ConditionEvaluation(
                condition_id=policy.condition_id,
                label="High risk",
                score=0,
                confidence=min(1.0, confidence + 0.20),
                reasons=[f"Restaurant lists {allergen} as an allergen"],
                matched_rules=[f"blocked_allergen:{allergen}"],
            )

    for tag in policy.blocked_tags:
        if tag.lower() in tags:
            return ConditionEvaluation(
                condition_id=policy.condition_id,
                label="High risk",
                score=10,
                confidence=min(1.0, confidence + 0.10),
                reasons=[f"Preparation indicates {tag}"],
                matched_rules=[f"blocked_tag:{tag}"],
            )

   
    inferred_block_triggered = False
    for ing in policy.blocked_ingredients:
        if _ingredient_matches(ing, inferred_ingredients):
            score -= 35
            confidence = max(0.05, confidence - 0.10)
            reasons.append(f"Recipe inference suggests possible {ing}")
            matched_rules.append(f"inferred_blocked_ingredient:{ing}")
            if not inferred_block_triggered:
                missing_info.append("Ingredient data inferred — explicit list not confirmed")
                inferred_block_triggered = True

    
    for ing in policy.caution_ingredients:
        if _ingredient_matches(ing, explicit_ingredients) or _ingredient_matches(ing, inferred_ingredients):
            score -= 25
            reasons.append(f"May include {ing}")
            matched_rules.append(f"caution_ingredient:{ing}")

    
    for tag in policy.caution_tags:
        if tag.lower() in tags:
            score -= 20
            reasons.append(f"Preparation suggests {tag}")
            matched_rules.append(f"caution_tag:{tag}")

    
    nutrition = item.nutrition_explicit or {}
    
    metric_hits: dict[str, tuple[float, str, str]] = {}

    for key, threshold in policy.thresholds.items():
        parts = key.rsplit("_", 1)
        if len(parts) != 2:
            continue
        metric, level = parts
        value = nutrition.get(metric)
        if value is None:
            continue
        if level == "caution" and value >= threshold:
            existing_penalty = metric_hits.get(metric, (0.0, "", ""))[0]
            if existing_penalty < 20.0:
                metric_hits[metric] = (
                    20.0,
                    f"{metric} is elevated ({value})",
                    f"threshold_caution:{metric}",
                )
        elif level == "risk" and value >= threshold:
            
            metric_hits[metric] = (
                45.0,
                f"{metric} is very high ({value})",
                f"threshold_risk:{metric}",
            )

    for penalty, reason, rule in metric_hits.values():
        score -= penalty
        reasons.append(reason)
        matched_rules.append(rule)

    
    if not item.ingredients_explicit:
        missing_info.append("No explicit ingredient list")
        score -= policy.uncertainty_penalty * 100

    if item.evidence_source_type == "generic_recipe":
        missing_info.append("Assessment partly based on common recipe patterns")
        score -= 20

    if item.uncertainty_flags:
        missing_info.extend(item.uncertainty_flags)
        score -= 10

    score = max(0, min(100, score))

    if score >= 75:
        label = "Compatible"
    elif score >= 45:
        label = "Caution"
    else:
        label = "Unclear" if missing_info else "High risk"

    return ConditionEvaluation(
        condition_id=policy.condition_id,
        label=label,
        score=score,
        confidence=confidence,
        reasons=reasons[:3],
        missing_info=missing_info[:3],
        matched_rules=matched_rules[:6],
    )
