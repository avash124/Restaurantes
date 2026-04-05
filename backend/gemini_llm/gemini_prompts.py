def build_extraction_prompt(page_bundle_text: str) -> str:
    return f"""
Convert the following restaurant website evidence into structured restaurant/menu data.

Requirements:
- Return restaurant_name, address, website_url
- For each menu item return:
  - name
  - category
  - description
  - ingredients_explicit
  - ingredients_inferred
  - allergens_explicit
  - preparation_tags
  - uncertainty_flags
  - nutrition_explicit
  - sourcing_notes
  - evidence_source_type
  - extraction_confidence

Evidence:
{page_bundle_text}
"""


def build_short_explanation_prompt(
    item_name: str,
    label: str,
    confidence_band: str,
    reasons: list[str],
    missing_info: list[str],
    ingredients: list[str] | None = None,
    condition_ids: list[str] | None = None,
) -> str:
    ingredient_line = (
        f"Known ingredients: {', '.join(ingredients)}" if ingredients else "Ingredients: not fully known"
    )
    condition_line = (
        f"User conditions: {', '.join(condition_ids)}" if condition_ids else "User conditions: unspecified"
    )
    return f"""
Write a concise 1-2 sentence safety explanation for a restaurant menu item.

Item: {item_name}
Safety label: {label}
Confidence: {confidence_band}
{ingredient_line}
{condition_line}
Evaluation reasons: {reasons}
Missing info: {missing_info}

Rules:
- Name specific ingredients from the item and explain concretely why they are safe or unsafe given the user's condition(s)
- If ingredients are unknown, say so and explain the uncertainty
- 1-2 sentences only — no lists, no bullet points
- Do not give medical advice or recommend consulting a doctor
"""