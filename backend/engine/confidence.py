from backend.models.menu_item import MenuItemFacts


def compute_confidence(item: MenuItemFacts) -> float:
   
    c = item.extraction_confidence

    # Provenance quality
    if item.evidence_source_type == "restaurant_explicit":
        c += 0.15   
    elif item.evidence_source_type == "restaurant_inferred":
        c -= 0.05   
    elif item.evidence_source_type == "generic_recipe":
        c -= 0.20   
    
    if not item.ingredients_explicit:
        c -= 0.15

    
    flag_count = len(item.uncertainty_flags)
    if flag_count == 1:
        c -= 0.10
    elif flag_count == 2:
        c -= 0.16
    elif flag_count >= 3:
        c -= 0.20

    
    if not item.description and not item.ingredients_explicit:
        c -= 0.10

    return max(0.05, min(1.0, c))
