from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models_db.evals import ConditionEvaluation


def upsert_condition_evaluation(
    session: Session,
    menu_item_id,
    evaluation,
) -> ConditionEvaluation:
    existing = (
        session.execute(
            select(ConditionEvaluation)
            .where(ConditionEvaluation.menu_item_id == menu_item_id)
            .where(ConditionEvaluation.condition_id == evaluation.condition_id)
        )
        .scalars()
        .first()
    )

    if existing:
        existing.label = evaluation.label
        existing.score = evaluation.score
        existing.confidence = evaluation.confidence
        existing.reasons = evaluation.reasons
        existing.missing_info = evaluation.missing_info
        existing.matched_rules = evaluation.matched_rules

        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    new_row = ConditionEvaluation(
        menu_item_id=menu_item_id,
        condition_id=evaluation.condition_id,
        label=evaluation.label,
        score=evaluation.score,
        confidence=evaluation.confidence,
        reasons=evaluation.reasons,
        missing_info=evaluation.missing_info,
        matched_rules=evaluation.matched_rules,
    )
    session.add(new_row)
    session.commit()
    session.refresh(new_row)
    return new_row