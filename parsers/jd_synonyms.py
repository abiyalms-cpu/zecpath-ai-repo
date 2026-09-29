"""
Lookup tables mapping variant wording to one canonical form.
"""

ROLE_SYNONYMS = {
    "Software Engineer": ["software engineer", "software developer", "sde ii", "sde 2", "sde"],
    "Sales Executive": ["sales executive"],
    "HR Manager": ["hr manager", "human resources manager"],
    "Financial Analyst": ["financial analyst"],
    "Digital Marketing Specialist": ["digital marketing specialist"],
    "Mechanical Engineer": ["mechanical design engineer", "mechanical engineer"],
    "Customer Support Executive": ["customer support executive"],
}

SKILL_SYNONYMS = {
    "Java": ["java"],
    "Python": ["python"],
    "JavaScript": ["javascript"],
    "React": ["reactjs", "react.js", "react"],
    "Node.js": ["node.js", "nodejs"],
    "SQL": ["sql databases", "sql"],
    "MySQL": ["mysql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"],
    "GraphQL": ["graphql"],
    "AWS": ["aws", "amazon web services"],
    "Docker": ["docker"],
    "REST APIs": ["rest apis", "restful apis", "rest api"],
    "Microservices": ["microservices"],
    "CI/CD": ["ci/cd", "ci-cd"],
    "Excel": ["advanced excel", "excel"],
    "Power BI": ["power bi", "powerbi"],
    "SAP FICO": ["sap fico"],
    "CRM": ["crm"],
    "Salesforce": ["salesforce"],
    "Zoho": ["zoho"],
    "HRIS": ["hris"],
    "Darwinbox": ["darwinbox"],
    "SAP SuccessFactors": ["sap successfactors", "successfactors"],
    "Google Ads": ["google ads"],
    "Meta Ads": ["meta ads", "facebook ads"],
    "SEO": ["seo"],
    "Google Analytics 4": ["google analytics 4", "ga4"],
    "Mailchimp": ["mailchimp"],
    "SolidWorks": ["solidworks"],
    "AutoCAD": ["autocad"],
    "GD&T": ["gd&t"],
    "DFMEA": ["dfmea"],
    "Lean Manufacturing": ["lean manufacturing"],
    "Zendesk": ["zendesk"],
    "Negotiation": ["negotiation"],
}


def _build_lookup(synonym_map):
    lookup = {}
    for canonical, variants in synonym_map.items():
        for variant in sorted(variants, key=len, reverse=True):
            lookup[variant.lower()] = canonical
    return lookup


ROLE_LOOKUP = _build_lookup(ROLE_SYNONYMS)
SKILL_LOOKUP = _build_lookup(SKILL_SYNONYMS)