from pydantic import BaseModel, Field
from typing import List, Literal, Optional



EvalLabel = Literal["Compatible", "Caution", "High risk", "Unclear"]


class ConditionEvaluation(BaseModel):
    condition_id: str
    label: EvalLabel
    score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)

    reasons: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)

    # Populated by the explanation layer after evaluation.
    short_explanation: Optional[str] = None
