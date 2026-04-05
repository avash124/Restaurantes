from typing import List

from backend.models.eval import ConditionEvaluation


LABEL_PRIORITY = {
    "High risk": 3,
    "Unclear": 2,
    "Caution": 1,
    "Compatible": 0,
}


def _deduplicated(items: List[str]) -> List[str]:
    """Preserve order while removing exact duplicates."""
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def aggregate_condition_results(results: List[ConditionEvaluation]) -> ConditionEvaluation:
    """
    Collapse per-condition evaluations into a single worst-case result.

    Strategy:
    - Label  : worst label by LABEL_PRIORITY
    - Score  : minimum across all conditions (weakest-link)
    - Confidence: minimum across all conditions (least certain source wins)
    - Reasons / missing_info / matched_rules: merged and deduplicated
    """
    if not results:
        return ConditionEvaluation(
            condition_id="combined",
            label="Unclear",
            score=0,
            confidence=0.05,
            reasons=["No evaluation results available"],
        )

    worst = max(results, key=lambda r: LABEL_PRIORITY[r.label])

    
    contributing_ids = [r.condition_id for r in results if r.condition_id != "combined"]
    combined_id = "combined[" + ", ".join(contributing_ids) + "]" if contributing_ids else "combined"

    all_reasons = _deduplicated([reason for r in results for reason in r.reasons])
    all_missing = _deduplicated([m for r in results for m in r.missing_info])
    all_rules = _deduplicated([mr for r in results for mr in r.matched_rules])

    return ConditionEvaluation(
        condition_id=combined_id,
        label=worst.label,
        score=min(r.score for r in results),
        confidence=min(r.confidence for r in results),
        reasons=all_reasons[:4],
        missing_info=all_missing[:4],
        matched_rules=all_rules[:8],
    )
