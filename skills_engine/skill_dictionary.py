"""
Master skill dictionary for Zecpath.

SKILL_CATALOG holds every skill we know about, grouped into three
categories (as the Day 9 brief asks for): technical, business, creative.

Each entry is keyed by its CANONICAL name — the name we normalize to —
and holds:
    category          : "technical" | "business" | "creative"
    synonyms           : other names/abbreviations for the exact same skill
    spelling_variants  : common misspellings or alternate spacing/casing

SKILL_STACKS holds named stacks (MERN, MEAN, LAMP) that expand into a
list of canonical skills. If a resume says "MERN", that's a signal the
candidate used all four underlying skills, even if they never typed
"MongoDB" or "Express" by name.
"""

SKILL_CATALOG = {
    # ---------------- technical ----------------
    "JavaScript": {
        "category": "technical",
        "synonyms": ["JS"],
        "spelling_variants": ["java script", "javscript"],
    },
    "TypeScript": {
        "category": "technical",
        "synonyms": ["TS"],
        "spelling_variants": ["type script"],
    },
    "Python": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": ["phyton"],
    },
    "Java": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "C++": {
        "category": "technical",
        "synonyms": ["Cpp"],
        "spelling_variants": [],
    },
    "C#": {
        "category": "technical",
        "synonyms": ["C Sharp"],
        "spelling_variants": [],
    },
    "PHP": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "HTML": {
        "category": "technical",
        "synonyms": ["HTML5"],
        "spelling_variants": [],
    },
    "CSS": {
        "category": "technical",
        "synonyms": ["CSS3"],
        "spelling_variants": [],
    },
    "React": {
        "category": "technical",
        "synonyms": ["React.js", "ReactJS"],
        "spelling_variants": [],
    },
    "Angular": {
        "category": "technical",
        "synonyms": ["AngularJS"],
        "spelling_variants": [],
    },
    "Vue.js": {
        "category": "technical",
        "synonyms": ["Vue", "VueJS"],
        "spelling_variants": [],
    },
    "Node.js": {
        "category": "technical",
        "synonyms": ["NodeJS", "Node"],
        "spelling_variants": ["node js"],
    },
    "Express.js": {
        "category": "technical",
        "synonyms": ["Express", "ExpressJS"],
        "spelling_variants": [],
    },
    "Django": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Flask": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "MongoDB": {
        "category": "technical",
        "synonyms": ["Mongo"],
        "spelling_variants": [],
    },
    "MySQL": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "PostgreSQL": {
        "category": "technical",
        "synonyms": ["Postgres"],
        "spelling_variants": [],
    },
    "SQL": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "AWS": {
        "category": "technical",
        "synonyms": ["Amazon Web Services"],
        "spelling_variants": [],
    },
    "Azure": {
        "category": "technical",
        "synonyms": ["Microsoft Azure"],
        "spelling_variants": [],
    },
    "Docker": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Git": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "REST API": {
        "category": "technical",
        "synonyms": ["RESTful API", "REST"],
        "spelling_variants": [],
    },
    "Firebase": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": [],
    },
    "jQuery": {
        "category": "technical",
        "synonyms": [],
        "spelling_variants": ["j query"],
    },
    "Tailwind CSS": {
        "category": "technical",
        "synonyms": ["TailwindCSS", "Tailwind"],
        "spelling_variants": [],
    },
    "Excel": {
        "category": "technical",
        "synonyms": ["MS Excel", "Microsoft Excel"],
        "spelling_variants": [],
    },
    "Power BI": {
        "category": "technical",
        "synonyms": ["PowerBI"],
        "spelling_variants": [],
    },
    "HRIS": {
        "category": "technical",
        "synonyms": ["Human Resource Information System", "Human Resources Information System"],
        "spelling_variants": [],
    },

    # ---------------- business ----------------
    "Sales": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Negotiation": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Business Development": {
        "category": "business",
        "synonyms": ["BD"],
        "spelling_variants": [],
    },
    "Financial Analysis": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Budgeting": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Forecasting": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Project Management": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Recruitment": {
        "category": "business",
        "synonyms": ["Talent Acquisition"],
        "spelling_variants": [],
    },
    "Payroll": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Vendor Management": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Market Research": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Customer Relationship Management": {
        "category": "business",
        "synonyms": ["CRM"],
        "spelling_variants": [],
    },
    "Operations Management": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Supply Chain Management": {
        "category": "business",
        "synonyms": [],
        "spelling_variants": [],
    },

    # ---------------- creative ----------------
    "Graphic Design": {
        "category": "creative",
        "synonyms": [],
        "spelling_variants": [],
    },
    "UI/UX Design": {
        "category": "creative",
        "synonyms": ["UX Design", "UI Design", "User Experience Design"],
        "spelling_variants": [],
    },
    "Figma": {
        "category": "creative",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Adobe Photoshop": {
        "category": "creative",
        "synonyms": ["Photoshop"],
        "spelling_variants": [],
    },
    "Adobe Illustrator": {
        "category": "creative",
        "synonyms": ["Illustrator"],
        "spelling_variants": [],
    },
    "Adobe XD": {
        "category": "creative",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Content Writing": {
        "category": "creative",
        "synonyms": ["Copywriting"],
        "spelling_variants": [],
    },
    "Video Editing": {
        "category": "creative",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Social Media Marketing": {
        "category": "creative",
        "synonyms": [],
        "spelling_variants": [],
    },
    "Digital Marketing": {
        "category": "creative",
        "synonyms": [],
        "spelling_variants": [],
    },
}

# Named skill stacks. A resume mentioning the stack name is treated as
# evidence for every skill it expands to.
SKILL_STACKS = {
    "MERN": ["MongoDB", "Express.js", "React", "Node.js"],
    "MEAN": ["MongoDB", "Express.js", "Angular", "Node.js"],
    "LAMP": ["Linux", "Apache", "MySQL", "PHP"],
}