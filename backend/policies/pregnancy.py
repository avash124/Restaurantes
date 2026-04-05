from backend.models.condition_policy import ConditionPolicy

pregnancy_policy = ConditionPolicy(
    condition_id="pregnancy",
    blocked_ingredients=[
        # ── Raw / undercooked fish and shellfish (listeria / parasites) ───────
        "raw fish", "sashimi", "sushi", "raw tuna", "raw salmon",
        "raw oyster", "raw clam", "raw mussel", "raw shellfish",
        # ── Raw / undercooked meat and poultry ────────────────────────────────
        "steak tartare", "beef tartare", "tuna tartare",
        "carpaccio", "bresaola",  # raw cured beef
        "raw chicken", "raw pork",
        # ── Raw eggs and preparations containing raw egg ──────────────────────
        "raw egg", "raw egg white", "raw egg yolk",
        "caesar dressing",       # traditional recipe uses raw egg
        "hollandaise",           # contains raw/barely cooked egg
        "bearnaise",
        "mayonnaise",            # homemade / unpasteurised versions
        "aioli",                 # traditional recipe uses raw egg
        "mousse",                # chocolate mousse often uses raw egg
        "tiramisu",              # contains raw egg and alcohol
        "eggnog",                # raw egg + alcohol
        # ── High-mercury fish (FDA guidance) ──────────────────────────────────
        "shark", "shark fin",
        "swordfish",
        "king mackerel",
        "tilefish",
        "orange roughy",
        "bigeye tuna",
        "marlin",
        # ── Alcohol ───────────────────────────────────────────────────────────
        "alcohol", "wine", "red wine", "white wine", "champagne", "prosecco",
        "beer", "ale", "lager", "cider",
        "spirits", "vodka", "whiskey", "rum", "gin", "tequila", "brandy",
        "sake", "soju", "liqueur",
        "wine sauce", "beer batter", "coq au vin", "beef bourguignon",
        "flambe", "rum cake", "tiramisu",
        # ── Liver and high-vitamin-A organ meats ──────────────────────────────
        "liver", "chicken liver", "beef liver", "lamb liver",
        "liver pate", "pate", "foie gras",
        # ── Unpasteurised dairy and soft cheeses (listeria) ───────────────────
        "unpasteurized cheese", "raw milk cheese",
        "brie", "camembert",         # soft-rind cheeses (unless pasteurised and cooked)
        "roquefort", "gorgonzola", "stilton", "blue cheese",
        "queso fresco", "queso blanco", "queso panela",
        "feta",                      # unless labelled pasteurised
        "soft goat cheese", "chevre",
    ],
    blocked_tags=[
        "raw", "undercooked", "rare", "blue_rare",
        "raw_fish", "raw_shellfish", "raw_egg",
        "unpasteurized", "unpasteurised",
        "high_mercury",
        "alcohol_based", "flambeed",
    ],
    caution_ingredients=[
        # ── Cold-smoked / cured seafood (listeria) ────────────────────────────
        "smoked salmon", "lox", "gravlax", "smoked trout",
        "cold-smoked fish", "smoked seafood",
        # ── Deli meats and processed meats (listeria) ─────────────────────────
        "deli meat", "deli turkey", "deli ham", "lunch meat",
        "cold cuts", "bologna", "salami", "pepperoni", "prosciutto",
        "hot dog", "frankfurter", "wiener",
        # ── Moderate-mercury fish (limit to 2 servings/week) ─────────────────
        "tuna", "canned tuna", "albacore tuna",
        "halibut", "mahi mahi", "grouper", "snapper", "sea bass",
        # ── Unpasteurised juices ──────────────────────────────────────────────
        "unpasteurized juice", "raw cider", "fresh-pressed juice",
        # ── Sprouts (bacterial contamination) ────────────────────────────────
        "sprouts", "alfalfa sprouts", "bean sprouts", "clover sprouts",
        "radish sprouts", "mung bean sprouts",
        # ── High-caffeine items ───────────────────────────────────────────────
        "caffeine", "espresso", "energy drink",
    ],
    caution_tags=[
        "runny_egg", "soft_cooked_egg", "poached_egg",
        "unclear_pasteurization", "cold_smoked",
        "may_contain_listeria", "high_caffeine",
        "cured_not_cooked", "medium_rare", "pink_inside",
        "refrigerated_ready_to_eat",
    ],
    uncertainty_penalty=0.20,
)
