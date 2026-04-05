from backend.models.condition_policy import ConditionPolicy

diabetes_policy = ConditionPolicy(
    condition_id="diabetes",
    # No absolute blocks — diabetes is managed through dietary choices, not strict exclusions.
    # High-glycaemic and sugar-dense ingredients are flagged at caution level.
    caution_ingredients=[
        # ── Direct / added sugars ──────────────────────────────────────────────
        "sugar", "white sugar", "brown sugar", "powdered sugar", "cane sugar",
        "raw sugar", "turbinado", "demerara", "palm sugar", "coconut sugar",
        "confectioners sugar", "icing sugar", "beet sugar",
        # ── Syrups and liquid sugars ───────────────────────────────────────────
        "corn syrup", "high fructose corn syrup", "hfcs", "maple syrup",
        "honey", "agave", "agave nectar", "molasses", "golden syrup",
        "rice syrup", "date syrup", "simple syrup", "cane syrup",
        "barley malt syrup", "glucose syrup",
        # ── Refined / high-GI starches ────────────────────────────────────────
        "white flour", "all-purpose flour", "white bread", "white rice",
        "white pasta", "instant oats", "instant rice", "cornstarch",
        "potato starch", "tapioca starch", "arrowroot",
        "white tortilla", "flour tortilla",
        # ── Sweets and confections ────────────────────────────────────────────
        "chocolate", "milk chocolate", "candy", "caramel", "toffee",
        "fudge", "marshmallow", "frosting", "icing", "glaze",
        "jam", "jelly", "preserves", "fruit spread", "marmalade",
        "lollipop", "gummy", "hard candy", "nougat",
        # ── Hidden / chemical sugars ──────────────────────────────────────────
        "condensed milk", "sweetened condensed milk", "sweet cream",
        "dextrose", "maltose", "maltodextrin", "glucose", "fructose",
        "sucrose", "sorbitol", "xylitol", "mannitol",
        "fruit juice concentrate", "apple juice", "grape juice",
        "orange juice", "sweet tea", "lemonade",
        # ── Desserts and baked goods ──────────────────────────────────────────
        "cake", "pastry", "pie", "cookie", "brownie", "donut", "muffin",
        "waffle", "crepe", "churro", "cannoli", "baklava", "tiramisu",
        "cheesecake", "pudding", "custard", "panna cotta", "gelatin dessert",
        "sorbet", "sherbet", "ice cream", "frozen yogurt",
        # ── Sweetened sauces and dressings ───────────────────────────────────
        "teriyaki sauce", "bbq sauce", "sweet chili sauce", "hoisin sauce",
        "honey mustard", "sweet and sour sauce", "ketchup",
        "sweetened dressing", "honey glaze",
    ],
    caution_tags=[
        "sweetened", "sugary", "dessert", "glazed", "candied",
        "frosted", "caramelized", "sugar_coated", "honey_drizzled",
        "fried", "battered", "deep_fried",
        "heavy_sauce", "sweet_sauce", "teriyaki", "bbq_sauce",
        "sugar_added", "high_glycemic", "syrup_based",
    ],
    thresholds={
        "sugar_g_caution": 10,
        "sugar_g_risk": 25,
        "added_sugar_g_caution": 8,
        "added_sugar_g_risk": 20,
        "carb_g_caution": 45,
        "carb_g_risk": 75,
    },
    uncertainty_penalty=0.12,
)
