from backend.models.condition_policy import ConditionPolicy

dairy_policy = ConditionPolicy(
    condition_id="dairy_allergy",
    blocked_ingredients=[
        # ── Liquid dairy ──────────────────────────────────────────────────────
        "milk", "whole milk", "skim milk", "low-fat milk", "nonfat milk",
        "buttermilk", "half and half", "evaporated milk", "condensed milk",
        "sweetened condensed milk", "dried milk", "milk powder", "milk solids",
        "cream", "heavy cream", "double cream", "whipping cream", "sour cream",
        "creme fraiche", "clotted cream",
        # ── Milk proteins ─────────────────────────────────────────────────────
        "whey", "whey protein", "casein", "caseinate", "sodium caseinate",
        "calcium caseinate", "lactalbumin", "lactoglobulin", "lactulose",
        "lactose",
        # ── Butter and related ────────────────────────────────────────────────
        "butter", "clarified butter", "ghee", "butter oil",
        # ── Yogurt and fermented dairy ────────────────────────────────────────
        "yogurt", "yoghurt", "kefir", "labneh",
        # ── Fresh cheeses ─────────────────────────────────────────────────────
        "cheese", "cream cheese", "cottage cheese", "ricotta", "mascarpone",
        "quark", "fromage frais", "queso fresco", "paneer", "halloumi",
        # ── Aged / hard cheeses ───────────────────────────────────────────────
        "cheddar", "mozzarella", "parmesan", "parmigiano", "gruyere",
        "emmental", "swiss cheese", "gouda", "edam", "manchego",
        "brie", "camembert", "feta", "blue cheese", "gorgonzola",
        "stilton", "roquefort", "pecorino", "provolone", "colby",
        "monterey jack", "pepper jack",
        # ── Frozen and dessert dairy ──────────────────────────────────────────
        "ice cream", "gelato", "frozen yogurt", "custard", "pudding",
        "milk chocolate", "white chocolate", "ganache",
        # ── Dairy in sauces ───────────────────────────────────────────────────
        "bechamel", "mornay", "alfredo", "cream sauce", "cheese sauce",
        "au gratin",
    ],
    blocked_allergens=["milk", "dairy", "lactose"],
    caution_tags=[
        "cross_contact_possible",
        "may_contain_dairy", "cream_sauce", "cheese_sauce",
        "butter_sauce", "butter_basted", "cheese_topped",
        "creamy", "gratin",
    ],
    uncertainty_penalty=0.25,
)
