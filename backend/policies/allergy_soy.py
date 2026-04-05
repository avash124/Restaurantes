from backend.models.condition_policy import ConditionPolicy

soy_policy = ConditionPolicy(
    condition_id="soy_allergy",
    blocked_ingredients=[
        # ── Whole soy ─────────────────────────────────────────────────────────
        "soy", "soya", "soybean", "soybeans", "soy bean",
        "edamame",
        # ── Soy protein products ──────────────────────────────────────────────
        "tofu", "firm tofu", "silken tofu", "soft tofu",
        "tempeh",
        "natto",
        "yuba", "tofu skin", "bean curd", "bean curd skin",
        "textured soy protein", "textured vegetable protein", "tvp",
        "soy protein", "soy protein isolate", "soy protein concentrate",
        "hydrolyzed soy protein", "hydrolyzed vegetable protein", "hvp",
        "soy flour", "soy meal",
        "soy milk", "soy cheese", "soy cream", "soy yogurt",
        # ── Soy-based sauces and condiments ──────────────────────────────────
        "soy sauce", "shoyu", "tamari",
        "miso", "miso paste", "white miso", "red miso",
        "teriyaki sauce",
        "hoisin sauce",
        "oyster sauce",          # often contains soy
        "worcestershire sauce",  # often contains soy
        "ponzu",
        "doubanjiang", "doenjang", "gochujang",  # fermented soy pastes
        # ── Soy oils / lecithin ───────────────────────────────────────────────
        "soy lecithin",          # used as emulsifier; may trigger in severe cases
        "soybean oil",           # typically refined (low allergen risk) but flag for severe allergy
        # ── Dishes commonly soy-based ────────────────────────────────────────
        "agedashi tofu", "mapo tofu", "stir fry sauce",
    ],
    blocked_allergens=["soy", "soya", "soybean"],
    caution_tags=[
        "cross_contact_possible",
        "asian_sauce", "stir_fry", "may_contain_soy",
        "marinated_in_soy", "soy_based_sauce", "wok_cooked",
        "japanese_style", "korean_style", "chinese_style",
    ],
    uncertainty_penalty=0.25,
)
