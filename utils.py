import random
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

EXCLUDE_PHRASES = [
    "visa sponsorship",
    "must be authorized to work",
    "work authorization required",
    "h1b",
    "h-1b",
    "green card",
    "us citizen only",
    "u.s. citizen only",
    "security clearance required",
    "requires clearance",
    "top secret",
]

SEARCH_KEYWORDS = [
    # Full Stack
    "Full Stack Developer remote",
    "Full Stack Engineer remote",
    "Senior Full Stack Developer remote",
    "Senior Full Stack Engineer remote",

    # MERN / MEAN / LAMP
    "MERN Stack Developer remote",
    "MERN Stack Engineer remote",
    "MEAN Stack Developer remote",
    "MEAN Stack Engineer remote",
    "LAMP Stack Developer remote",
    "LAMP Stack Engineer remote",
    "Senior MERN Developer remote",
    "Senior MERN Engineer remote",

    # Frontend
    "Frontend Developer remote",
    "Frontend Engineer remote",
    "React Developer remote",
    "React Engineer remote",
    "Angular Developer remote",
    "Angular Engineer remote",
    "Next.js Developer remote",
    "Next.js Engineer remote",
    "Vue.js Developer remote",
    "Vue.js Engineer remote",

    # Backend
    "Backend Developer remote",
    "Backend Engineer remote",
    "Node.js Developer remote",
    "Node.js Engineer remote",
    "Python Developer remote",
    "Python Engineer remote",
    "Django Developer remote",
    "Django Engineer remote",
    "Laravel Developer remote",
    "Laravel Engineer remote",
    "PHP Developer remote",
    "PHP Engineer remote",
    "Ruby on Rails Developer remote",
    "Ruby on Rails Engineer remote",
    "Spring Boot Developer remote",
    "Spring Boot Engineer remote",
    "Java Developer remote",
    "Java Engineer remote",

    # JavaScript / TypeScript / GraphQL
    "JavaScript Developer remote",
    "JavaScript Engineer remote",
    "TypeScript Developer remote",
    "TypeScript Engineer remote",
    "GraphQL Developer remote",
    "GraphQL Engineer remote",

    # .NET / Microsoft
    ".NET Developer remote",
    ".NET Engineer remote",
    "C# Developer remote",
    "C# Engineer remote",

    # Mobile
    "React Native Developer remote",
    "React Native Engineer remote",
    "Flutter Developer remote",
    "Flutter Engineer remote",

    # DevOps / Cloud / Infrastructure
    "DevOps Engineer remote",
    "AWS Cloud Engineer remote",
    "Azure Cloud Engineer remote",
    "GCP Engineer remote",
    "Cloud Engineer remote",
    "Kubernetes Engineer remote",
    "Terraform Engineer remote",
    "Site Reliability Engineer remote",
    "Platform Engineer remote",

    # Other
    "Golang Developer remote",
    "Golang Engineer remote",
    "ServiceNow Developer remote",
]

REGION_KEYWORDS = {
    "US Remote": [
        "us remote", "united states remote", "remote usa", "remote us", "anywhere in us",
        "remote (us)", "remote - us", "remote, us", "usa remote", "remote united states",
    ],
    "Europe": ["europe", "european union", "eu remote", "remote europe", "emea", "remote - eu"],
    "Australia": ["australia", "au remote", "remote australia", "remote - au"],
    "New Zealand": ["new zealand", "nz remote", "remote nz", "remote - nz"],
    "Canada": ["canada", "ca remote", "remote canada", "remote - ca"],
    "UK": ["united kingdom", "uk remote", "remote uk", "great britain", "remote - uk"],
    "Worldwide": [
        "worldwide", "anywhere", "global", "international", "work from anywhere",
        "fully remote", "100% remote", "remote worldwide", "remote (worldwide)",
    ],
}


def get_random_user_agent():
    return random.choice(USER_AGENTS)


def should_exclude(text: str):
    """Returns (True, matched_phrase) if job should be excluded, else (False, None)."""
    text_lower = (text or "").lower()
    for phrase in EXCLUDE_PHRASES:
        if phrase in text_lower:
            return True, phrase
    return False, None


def detect_region(location_text: str, description_text: str = "") -> str:
    combined = (location_text + " " + description_text).lower()
    for region, keywords in REGION_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return region
    if "remote" in combined:
        return "Worldwide"
    return "Unknown"


def is_remote_job(location_text: str, description_text: str = "") -> bool:
    combined = (location_text + " " + description_text).lower()
    # Flag onsite-only jobs: has "onsite"/"on-site" and no "remote"
    if ("onsite" in combined or "on-site" in combined) and "remote" not in combined:
        return False
    return any(t in combined for t in [
        "remote", "work from home", "wfh", "distributed", "anywhere",
        "worldwide", "global", "international",
    ])


def extract_rate(text: str) -> str:
    if not text:
        return "Not specified"
    patterns = [
        r"\$[\d,]+\s*(?:k|K)?(?:\s*[-–]\s*\$[\d,]+\s*(?:k|K)?)?(?:\s*/\s*(?:hr|hour|yr|year|month|mo|annum|ann))?",
        r"[\d,]+\s*(?:USD|CAD|GBP|EUR|AUD)(?:\s*[-–]\s*[\d,]+\s*(?:USD|CAD|GBP|EUR|AUD))?",
        r"(?:USD|CAD|GBP|EUR|AUD)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "Not specified"


def core_term(keyword: str) -> str:
    term = keyword.lower()
    for w in [" remote", " developer", " engineer", " senior", " junior", " stack"]:
        term = term.replace(w, "")
    return term.strip()
