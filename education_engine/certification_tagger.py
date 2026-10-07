import re

CATEGORY_KEYWORDS = {
    "Technology": ["aws", "azure", "cloud", "sap", "erp", "developer", "software",
                   "front-end", "front end", "database", "salesforce", "programming"],
    "Finance": ["cfa", "finance", "financial", "accounting"],
    "Healthcare": ["life support", "bls", "acls", "cpr", "nursing", "medical", "clinical"],
    "Engineering": ["solidworks", "autocad", "cswa", "mechanical", "civil engineering"],
    "Design": ["ux", "ui", "design", "graphic", "adobe", "figma"],
    "Business": ["shrm", "hr", "human resources", "marketing", "ads", "hubspot",
                 "six sigma", "lean", "pmp", "project management", "operations"],
}

# Order matters: first matching category wins when a cert name could hint at more than one.
_CATEGORY_ORDER = ["Technology", "Finance", "Healthcare", "Engineering", "Design", "Business"]


def categorize_certification(name):
    name_lower = name.lower()
    for category in _CATEGORY_ORDER:
        for keyword in CATEGORY_KEYWORDS[category]:
            pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
            if re.search(pattern, name_lower):
                return category
    return "Uncategorized"


def tag_certifications(parsed_certifications):
    tagged = []
    for cert in parsed_certifications:
        tagged.append({**cert, "category": categorize_certification(cert["certification_name"])})
    return tagged