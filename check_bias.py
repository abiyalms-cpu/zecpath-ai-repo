import json
from fairness_engine.bias_analysis import (
    check_header_independence,
    format_bias_check,
    keyword_dependence_check,
)

results = {
    "header_independence": check_header_independence(),
    "format_bias": format_bias_check("data/segmented", "data/skills", "data/experience"),
    "keyword_dependence_sde_ii": keyword_dependence_check(
        "data/candidate_scores", "sde_ii", top_n=5
    ),
}

print(json.dumps(results, indent=2))

with open("data/fairness_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)