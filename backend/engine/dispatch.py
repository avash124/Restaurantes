from typing import List

from backend.models.menu_item import MenuItemFacts
from backend.models.eval import ConditionEvaluation
from backend.engine.basic_eval import evaluate_condition
from backend.policies.registry import POLICY_MAP


def evaluate_item_for_condition(item: MenuItemFacts, condition_id: str) -> ConditionEvaluation:
    policy = POLICY_MAP.get(condition_id)

    if not policy:
        supported = ", ".join(sorted(POLICY_MAP.keys()))
        return ConditionEvaluation(
            condition_id=condition_id,
            label="Unclear",
            score=0,
            confidence=0.05,
            reasons=[f"'{condition_id}' is not a supported condition"],
            missing_info=[f"Supported conditions: {supported}"],
        )

    return evaluate_condition(item, policy)


def supported_conditions() -> List[str]:
    return sorted(POLICY_MAP.keys())
