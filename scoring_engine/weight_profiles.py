# Each profile's weights sum to 1.0. Chosen by role category, not per-JD guessing:
# a technical role leans on skill match; an HR/finance role leans on education,
# since a relevant degree genuinely matters more there than it does for a developer.
WEIGHT_PROFILES = {
    "technical": {
        "skill_match": 0.40,
        "experience_relevance": 0.25,
        "education_alignment": 0.10,
        "semantic_similarity": 0.25,
    },
    "education_heavy": {
        "skill_match": 0.20,
        "experience_relevance": 0.20,
        "education_alignment": 0.40,
        "semantic_similarity": 0.20,
    },
    "default": {
        "skill_match": 0.30,
        "experience_relevance": 0.30,
        "education_alignment": 0.20,
        "semantic_similarity": 0.20,
    },
}

# Maps each real JD (by filename, not title — Day 12 found two JDs share a title)
# to the weight profile that fits its role category.
JD_PROFILE_MAP = {
    "sde_ii": "technical",
    "software_developer": "technical",
    "mechanical_engineer": "technical",
    "hr_manager": "education_heavy",
    "financial_analyst": "education_heavy",
    "digital_marketing": "default",
    "sales_executive": "default",
    "customer_support": "default",
}


def get_weight_profile(jd_file):
    profile_name = JD_PROFILE_MAP.get(jd_file, "default")
    return WEIGHT_PROFILES[profile_name]