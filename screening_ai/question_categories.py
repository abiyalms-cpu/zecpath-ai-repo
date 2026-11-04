"""
The seven screening-call categories from the PRD (Phase 5 — "AI Screening
Conversation Flow") and Day 22's own task list, in the order the AI call
asks them. Kept as a single source of truth so a category name is never
typed differently in two places.
"""

CATEGORIES = [
    {"key": "introduction", "label": "Introduction", "order": 1},
    {"key": "education", "label": "Education", "order": 2},
    {"key": "experience", "label": "Experience", "order": 3},
    {"key": "skills", "label": "Skills", "order": 4},
    {"key": "location", "label": "Location", "order": 5},
    {"key": "salary", "label": "Salary", "order": 6},
    {"key": "notice_period", "label": "Notice Period", "order": 7},
]

CATEGORY_KEYS = [c["key"] for c in CATEGORIES]


def category_label(key):
    return next((c["label"] for c in CATEGORIES if c["key"] == key), None)