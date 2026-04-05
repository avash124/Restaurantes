from pydantic import BaseModel, Field
from typing import Dict, List


class ConditionPolicy(BaseModel):
    condition_id: str

    blocked_ingredients: List[str] = Field(default_factory=list)
    blocked_allergens: List[str] = Field(default_factory=list)
    blocked_tags: List[str] = Field(default_factory=list)

    caution_ingredients: List[str] = Field(default_factory=list)
    caution_tags: List[str] = Field(default_factory=list)

    
    thresholds: Dict[str, float] = Field(default_factory=dict)

    
    uncertainty_penalty: float = Field(default=0.15, ge=0.0, le=1.0)
