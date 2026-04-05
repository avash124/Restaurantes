from backend.policies.diabetes import diabetes_policy
from backend.policies.high_chol import cholesterol_policy
from backend.policies.celiac import celiac_policy
from backend.policies.allergy_nut import nut_policy
from backend.policies.allergy_shellfish import shellfish_policy
from backend.policies.allergy_soy import soy_policy
from backend.policies.allergy_dairy import dairy_policy
from backend.policies.pregnancy import pregnancy_policy

POLICY_MAP = {
    "diabetes": diabetes_policy,
    "high_cholesterol": cholesterol_policy,
    "celiac": celiac_policy,
    "nut_allergy": nut_policy,
    "shellfish_allergy": shellfish_policy,
    "soy_allergy": soy_policy,
    "dairy_allergy": dairy_policy,
    "pregnancy": pregnancy_policy,
}