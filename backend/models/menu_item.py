from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional

from backend.models.eval import ConditionEvaluation



EvidenceSourceType = Literal["restaurant_explicit", "restaurant_inferred", "generic_recipe"]


class MenuItemFacts(BaseModel):
   
    name: str
    category: Optional[str] = None
    description: Optional[str] = None

    
    ingredients_explicit: List[str] = Field(default_factory=list)
    ingredients_inferred: List[str] = Field(default_factory=list)
    allergens_explicit: List[str] = Field(default_factory=list)
    preparation_tags: List[str] = Field(default_factory=list)

    
    uncertainty_flags: List[str] = Field(default_factory=list)

    
    nutrition_explicit: Dict[str, float] = Field(default_factory=dict)

    
    evidence_source_type: EvidenceSourceType = "restaurant_explicit"
    extraction_confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    
    final_label: Optional[str] = None
    final_score: Optional[float] = None
    final_confidence: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    short_explanation: Optional[str] = None

    
    per_condition_results: List[ConditionEvaluation] = Field(default_factory=list)


class NormalizedRestaurant(BaseModel):
    name: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    cuisine: Optional[str] = None
    website_url: Optional[str] = None
    menu_items: List[MenuItemFacts] = Field(default_factory=list)
