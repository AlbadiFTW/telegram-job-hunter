# ============================================================
# Job Scraper Configuration
# Tailored for: Abdul Rahman Albadi
# Scope: Abu Dhabi emirate (Abu Dhabi + Al Ain) · Emiratization roles only
#        · roles needing 0-3 years of experience
# ============================================================

# --- Telegram Settings ---
# Get these by messaging @BotFather on Telegram
# Keep placeholders here — real values go in .env file
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# ============================================================
# WHERE TO SEARCH — Abu Dhabi and Al Ain only
# ============================================================

LOCATIONS = [
    "Al Ain, Abu Dhabi, United Arab Emirates",
    "Abu Dhabi, United Arab Emirates",
]

# A job is kept ONLY if its location text contains one of these.
# (Dubai, Sharjah, a bare "United Arab Emirates", other countries... are all dropped.)
ALLOWED_LOCATION_MARKERS = [
    "al ain", "alain", "al-ain", "abu dhabi", "abudhabi",
    "al dhafra", "ruwais", "madinat zayed", "liwa", "ghayathi",
    "mussafah", "musaffah", "khalifa city", "yas island", "saadiyat",
    "masdar", "al reem", "reem island", "al maryah", "adgm", "zayed city",
    "al wathba", "al shamkha", "al raha", "al bahia", "shakhbout", "baniyas",
]

# Jobs in Al Ain get ranked first.
PRIORITY_LOCATIONS = ["al ain", "alain", "al-ain"]
PRIORITY_LOCATION_BONUS = 2

# Employers you actively want to hear about (matched against company name).
PREFERRED_COMPANIES = ["aloft", "hilton"]
PREFERRED_COMPANY_BONUS = 2

# ============================================================
# EMIRATIZATION FILTER
# ============================================================

# True  -> ONLY send roles aimed at UAE nationals
# False -> send everything relevant (Emirati roles still ranked first)
EMIRATI_ONLY = True
EMIRATI_BONUS = 5

# Matched in the job TITLE.
EMIRATI_TITLE_KEYWORDS = [
    "emirati", "emiratis", "uae national", "uae nationals", "emiratization",
    "emiratisation", "national talent", "nationals only", "national graduate",
]
# Matched in the job DESCRIPTION. Stricter on purpose, so "Emirati cuisine" at a
# restaurant doesn't count as an Emiratization role.
EMIRATI_DESCRIPTION_KEYWORDS = [
    "uae national", "uae nationals", "emiratization", "emiratisation",
    "emirati national", "emirati nationals", "emirati candidate",
    "emirati candidates", "emirati graduate", "emirati graduates",
    "emiratis only", "open to emiratis", "for emiratis", "national talent",
    "nationals only", "local nationals", "emirati applicants",
    "uae citizens", "uae citizen",
    # Arabic
    "مواطن إماراتي", "مواطنين إماراتيين", "الإماراتيين", "إماراتيين",
    "التوطين", "توطين", "مواطني الدولة",
]

# ============================================================
# EXPERIENCE FILTER
# ============================================================

# Skip a job if its description asks for MORE than this many years of experience.
# "3-5 years" (minimum 3) still passes. Jobs that don't state years are kept.
MAX_YEARS_EXPERIENCE = 3

# ============================================================
# WHAT TO SEARCH FOR (LinkedIn searches)
# ============================================================
# The search terms are Emirati-focused. The scraper then opens each result to read
# the full description, so it can confirm it really is an Emiratization role and
# check the experience requirement.

KEYWORDS_BY_SECTOR = {
    "core": [
        "Emirati",
        "UAE national",
        "Emiratization",
        "national graduate program",
        "Emirati graduate",
        "national talent program",
    ],
    "hospitality": [
        "Emirati hotel",
        "Emirati guest relations",
        "Emirati front office",
        "Emirati hospitality",
    ],
    "office_admin_hr": [
        "Emirati customer service",
        "Emirati administrative",
        "Emirati HR",
        "Emirati executive assistant",
        "Emirati receptionist",
    ],
    "business": [
        "Emirati sales",
        "Emirati marketing",
        "Emirati banking",
        "Emirati business analyst",
        "Emirati operations",
    ],
    "tech": [
        "Emirati developer",
        "Emirati software engineer",
        "Emirati IT",
    ],
}

ENABLED_SECTORS = ["core", "hospitality", "office_admin_hr", "business", "tech"]

# How many result pages (25 jobs each) to read per keyword. Core terms get 2 pages.
PAGES_PER_SECTOR = {"core": 2}
DEFAULT_PAGES = 1

SEARCH_KEYWORDS = [kw for sector in ENABLED_SECTORS for kw in KEYWORDS_BY_SECTOR[sector]]
SEARCH_QUERIES = [
    (kw, PAGES_PER_SECTOR.get(sector, DEFAULT_PAGES))
    for sector in ENABLED_SECTORS for kw in KEYWORDS_BY_SECTOR[sector]
]

# LinkedIn "posted within" window: r86400 = 24h, r172800 = 48h, r604800 = 7 days.
# Tip: use r604800 for ONE run to catch up on the past week, then switch back.
LINKEDIN_TIME_WINDOW = "r86400"

# Max job pages opened per run to read the full description (the slow part).
# Jobs not reached this run are picked up next run.
MAX_DETAIL_FETCHES_PER_RUN = 120

# ============================================================
# JOB BOARDS
# ============================================================
# Only LinkedIn is on. Indeed was removed. Naukrigulf can't be added with this kind
# of scraper (see README). The three boards below are kept in the code but OFF:
# they only show job titles, so an Emiratization role is only recognised if the
# title itself says so.
ENABLED_SOURCES = {
    "linkedin": True,
    "bayt": False,
    "gulftalent": False,
    "dubizzle": False,
}

# ============================================================
# RELEVANCE SCORING
# ============================================================
# base score = boosts + sector words in title + seniority penalties
# A job is dropped if its base score is below MIN_SCORE (0 = "not penalised into the ground").
# Al Ain / preferred-employer / Emirati bonuses are added AFTER this check, for ranking.
MIN_SCORE = 0

# Boosts: matched in title + description (whole words / phrases only)
SCORE_BOOST_KEYWORDS = [
    # entry level
    ("junior", 2), ("graduate", 2), ("entry level", 2), ("entry-level", 2),
    ("fresh graduate", 2), ("fresher", 2), ("0-2 years", 2), ("0-1 year", 2),
    ("trainee", 2), ("intern", 2), ("internship", 2), ("management trainee", 2),
    # tech stack
    ("react", 1), ("next.js", 2), ("nextjs", 1), ("node", 1),
    ("node.js", 1), ("nodejs", 1), ("python", 1), ("typescript", 2),
    ("javascript", 1), ("full stack", 1), ("fullstack", 1),
    ("express", 1), ("postgresql", 1), ("prisma", 2), ("tailwind", 1),
    ("rest api", 1), ("jwt", 1), ("socket.io", 2),
]

# Sector words matched in the job TITLE only (+1 each)
SECTOR_TITLE_KEYWORDS = [
    "receptionist", "front office", "front desk", "guest", "hotel",
    "hospitality", "concierge", "reservations", "food and beverage",
    "restaurant", "events", "customer service", "customer experience",
    "administrative", "administrator", "assistant", "coordinator", "officer",
    "analyst", "executive", "hr", "recruitment", "procurement", "logistics",
    "operations", "banking", "relationship", "marketing", "sales", "public relations",
    "teaching", "research", "document controller", "data entry",
    "developer", "engineer", "software", "programmer",
]

# Penalties: matched in the job TITLE only
SCORE_PENALTY_KEYWORDS = [
    ("senior", -4), ("sr", -4), ("lead", -3), ("principal", -4),
    ("architect", -3), ("head of", -4), ("director", -4),
    ("manager", -3), ("vp", -4), ("vice president", -4), ("chief", -4),
]

# ============================================================
# HARD REJECTS
# ============================================================

# Skipped if found in the job TITLE (whole-word match).
REJECT_TITLE_KEYWORDS = [
    # low-wage / not-a-fit roles
    "driver", "cleaner", "labourer", "laborer", "helper", "housemaid",
    "office boy", "tea boy", "security guard", "watchman", "dishwasher",
    # commission-only style / scammy
    "telesales", "door to door", "commission", "mlm", "network marketing",
    # tech stacks / paths you don't want
    "c++", "embedded", "sap", "salesforce", "mainframe", "cobol",
    "odoo functional", "php", "wordpress", "laravel",
    "devops", "triage", "kubernetes", "terraform", "argocd", "jenkins",
    "sre", "site reliability",
]

# Skipped if found anywhere in title OR description.
REJECT_ANYWHERE_KEYWORDS = [
    # nationality-restricted to other countries
    "saudi nationals", "saudization", "saudi national", "omani nationals",
    "omanization", "omani national", "qatari nationals", "qatarization",
    "kuwaiti nationals", "bahraini nationals",
    # scams / paid-to-apply schemes
    "commission only", "100% commission", "registration fee",
    "training fee", "investment required", "pay to apply",
]

# ============================================================
# TELEGRAM
# ============================================================
TELEGRAM_MAX_CHARS = 3900    # Telegram limit is 4096, leave margin
TELEGRAM_SEND_DELAY_SEC = 1.1

# With a narrow filter many runs find nothing. False = stay quiet on empty runs.
SEND_EMPTY_NOTICE = False

# --- File to track seen jobs (also remembers jobs checked and rejected) ---
SEEN_JOBS_FILE = "seen_jobs.json"

# --- Max jobs sent per run (best-scoring first; split over several Telegram messages) ---
MAX_JOBS_PER_RUN = 40