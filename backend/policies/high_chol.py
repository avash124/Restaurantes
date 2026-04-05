from backend.models.condition_policy import ConditionPolicy

cholesterol_policy = ConditionPolicy(
    condition_id="high_cholesterol",
    caution_ingredients=[
        # ── Animal fats and rendered fats ─────────────────────────────────────
        "butter", "ghee", "lard", "tallow", "duck fat", "schmaltz",
        "beef dripping", "suet",
        # ── High-fat dairy ────────────────────────────────────────────────────
        "cream", "heavy cream", "double cream", "whipping cream",
        "half and half", "sour cream", "creme fraiche", "clotted cream",
        "cream cheese", "full-fat cheese", "cheddar", "brie", "camembert",
        "blue cheese", "gorgonzola", "stilton", "gouda", "gruyere",
        "parmesan", "aged cheese", "whole milk", "condensed milk",
        # ── Processed / cured meats ───────────────────────────────────────────
        "bacon", "streaky bacon", "back bacon", "pancetta", "guanciale",
        "sausage", "bratwurst", "chorizo", "salami", "pepperoni",
        "hot dog", "frankfurter", "bologna", "mortadella", "liverwurst",
        "spam", "pate", "liver pate",
        # ── Fatty cuts of meat ────────────────────────────────────────────────
        "ribeye", "rib-eye", "prime rib", "short rib", "brisket",
        "pork belly", "duck leg", "chicken skin", "lamb shank",
        "lamb chop", "spare rib",
        # ── Organ meats ───────────────────────────────────────────────────────
        "liver", "kidney", "heart", "brain", "sweetbread", "tripe",
        # ── Tropical and hydrogenated oils ───────────────────────────────────
        "palm oil", "palm kernel oil", "coconut oil", "coconut cream",
        "coconut milk", "hydrogenated oil", "partially hydrogenated",
        "shortening", "vegetable shortening",
        # ── Egg yolk (high dietary cholesterol) ──────────────────────────────
        "egg yolk", "egg yolks", "whole egg",
        # ── Rich sauces and dressings ─────────────────────────────────────────
        "hollandaise", "bearnaise", "bechamel", "alfredo", "carbonara",
        "cream sauce", "cheese sauce", "aioli", "mayonnaise", "ranch",
        "caesar dressing",
        # ── Trans-fat-risk baked and fried items ─────────────────────────────
        "croissant", "puff pastry", "shortcrust pastry", "pie crust",
        "doughnut", "donut", "fried dough",
        # ── Shellfish high in dietary cholesterol ─────────────────────────────
        "shrimp", "prawn", "lobster", "crab",
    ],
    caution_tags=[
        "fried", "deep_fried", "pan_fried", "shallow_fried",
        "butter_basted", "butter_sauteed", "rendered_fat",
        "creamy_sauce", "cream_sauce", "cheese_sauce", "cheese_topped",
        "processed_meat", "high_fat", "lard_cooked",
        "pastry_wrapped", "en_croute",
    ],
    thresholds={
        "sat_fat_g_caution": 5,
        "sat_fat_g_risk": 10,
        "trans_fat_g_caution": 0.5,
        "trans_fat_g_risk": 2,
        "cholesterol_mg_caution": 150,
        "cholesterol_mg_risk": 300,
        "total_fat_g_caution": 20,
        "total_fat_g_risk": 35,
    },
    uncertainty_penalty=0.10,
)
