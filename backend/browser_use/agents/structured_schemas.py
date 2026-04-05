from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict


class WideRestaurantRecord(BaseModel):
    name: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    cuisine: Optional[str] = None
    website_url: Optional[str] = None
    menu_url: Optional[str] = None
    discovery_confidence: float = 0.5


class WideDiscoveryOutput(BaseModel):
    restaurants: List[WideRestaurantRecord] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: dict) -> dict:
        if isinstance(data, dict) and data.get("restaurants") is None:
            data["restaurants"] = []
        return data


class DeepMenuItemRecord(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None

    ingredients_explicit: List[str] = Field(default_factory=list)
    ingredients_inferred: List[str] = Field(default_factory=list)
    allergens_explicit: List[str] = Field(default_factory=list)
    preparation_tags: List[str] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)

    nutrition_explicit: Dict[str, float] = Field(default_factory=dict)
    sourcing_notes: List[str] = Field(default_factory=list)

    evidence_source_type: str = "restaurant_explicit"
    extraction_confidence: float = 0.5

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        for field in ("ingredients_explicit", "ingredients_inferred", "allergens_explicit",
                      "preparation_tags", "uncertainty_flags", "sourcing_notes"):
            if data.get(field) is None:
                data[field] = []
        if data.get("nutrition_explicit") is None:
            data["nutrition_explicit"] = {}
        return data


class DeepRestaurantOutput(BaseModel):
    restaurant_name: str
    address: str
    website_url: Optional[str] = None
    menu_items: List[DeepMenuItemRecord] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: dict) -> dict:
        if isinstance(data, dict) and data.get("menu_items") is None:
            data["menu_items"] = []
        return data