from sqlalchemy.orm import Session

from backend.database.models_db.menu_item import MenuItem, MenuItemFacts


def create_menu_item(session: Session, restaurant_id, item_data: dict) -> MenuItem:
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=item_data["name"],
        category=item_data.get("category"),
        description=item_data.get("description"),
        price=item_data.get("price"),
        evidence_source_type=item_data.get("evidence_source_type", "restaurant_explicit"),
        extraction_confidence=item_data.get("extraction_confidence", 0.0),
    )
    session.add(item)
    session.flush()

    facts = MenuItemFacts(
        menu_item_id=item.id,
        ingredients_explicit=item_data.get("ingredients_explicit", []),
        ingredients_inferred=item_data.get("ingredients_inferred", []),
        allergens_explicit=item_data.get("allergens_explicit", []),
        preparation_tags=item_data.get("preparation_tags", []),
        uncertainty_flags=item_data.get("uncertainty_flags", []),
        nutrition_explicit=item_data.get("nutrition_explicit", {}),
    )
    session.add(facts)
    session.commit()
    session.refresh(item)
    return item