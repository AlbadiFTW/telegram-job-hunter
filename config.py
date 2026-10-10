# ============================================================
# Job Scraper Configuration
# Tailored for: Abdul Rahman Albadi
# Scope: UAE only · all sectors · Al Ain is a priority location
# ============================================================

# --- Telegram Settings ---
# Get these by messaging @BotFather on Telegram
# Keep placeholders here — real values go in .env file
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# ============================================================
# WHERE TO SEARCH (UAE only)
# ============================================================

# Scraper searches every keyword in each location below.
# "Al Ain" is searched separately so it isn't buried under Dubai/Abu Dhabi listings.
LOCATIONS = [
    "Al Ain, Abu Dhabi, United Arab Emirates",
    "United Arab Emirates",          # nationwide: Dubai, Abu Dhabi, Sharjah, ...
]

# Jobs whose location contains one of these get a score bonus (sorted to the top).
PRIORITY_LOCATIONS = ["al ain", "al-ain", "alain"]
PRIORITY_LOCATION_BONUS = 2

# Employers you actively want to hear about (matched against company name).
PREFERRED_COMPANIES = ["aloft", "hilton"]
PREFERRED_COMPANY_BONUS = 2

# A job is kept only if its location text looks like the UAE.
# Anything mentioning another country is dropped (see FOREIGN_LOCATION_MARKERS).
UAE_LOCATION_MARKERS = [
    "uae", "united arab emirates", "ae", "emirates",
    "al ain", "abu dhabi", "dubai", "sharjah", "ajman", "umm al quwain",
    "umm al-quwain", "ras al khaimah", "ras al-khaimah", "rak", "fujairah",
    "fujeirah", "khor fakkan", "khorfakkan", "al dhafra", "ruwais", "liwa",
    "madinat zayed", "ghayathi", "masdar", "yas island", "saadiyat",
    "jebel ali", "dubai silicon oasis", "difc", "adgm",
]
FOREIGN_LOCATION_MARKERS = [
    "oman", "muscat", "salalah", "sohar", "qatar", "doha", "saudi", "riyadh",
    "jeddah", "dammam", "khobar", "kuwait", "bahrain", "manama", "egypt",
    "cairo", "jordan", "amman", "lebanon", "beirut", "india", "pakistan",
    "united kingdom", "london", "united states", "remote - worldwide",
]

# ============================================================
# WHAT TO SEARCH FOR (grouped by sector — switch groups on/off)
# ============================================================

KEYWORDS_BY_SECTOR = {
    # Roles aimed at UAE nationals (Emiratization / national graduate programmes)
    "emirati": [
        "Emirati",
        "UAE national",
        "Emiratization",
        "national graduate program",
        "Emirati graduate",
        "national talent program",
    ],
    "hospitality": [
        "hotel receptionist",
        "front office",
        "guest relations",
        "guest service agent",
        "hospitality trainee",
        "reservations agent",
        "concierge",
        "food and beverage",
        "restaurant supervisor",
        "events coordinator",
    ],
    "office_admin_hr": [
        "customer service",
        "administrative assistant",
        "executive assistant",
        "HR coordinator",
        "recruitment coordinator",
        "receptionist",
        "operations coordinator",
        "project coordinator",
        "data entry",
        "document controller",
    ],
    "business": [
        "business analyst",
        "sales executive",
        "marketing coordinator",
        "public relations",
        "relationship officer",
        "banking",
        "procurement",
        "logistics coordinator",
        "research assistant",
        "teaching assistant",
    ],
    "tech": [
        "full stack developer",
        "software engineer",
        "backend developer",
        "frontend developer",
        "React developer",
        "Node.js developer",
        "Next.js developer",
        "Python developer",
        "junior software engineer",
        "graduate software engineer",
    ],
}

# Comment a sector out to skip it. Fewer sectors = faster runs.
ENABLED_SECTORS = ["emirati", "hospitality", "office_admin_hr", "business", "tech"]

SEARCH_KEYWORDS = [kw for sector in ENABLED_SECTORS for kw in KEYWORDS_BY_SECTOR[sector]]

# ============================================================
# WHERE TO SEARCH (job boards)
# ============================================================

ENABLED_SOURCES = {
    "linkedin": True,
    "indeed": True,      # via the python-jobspy library (ae.indeed.com)
    "bayt": True,
    "gulftalent": True,
    "dubizzle": True,
    # Wuzzuf removed: it is an Egypt-focused board, not a UAE one.
}

# Indeed (JobSpy) settings
INDEED_RESULTS_WANTED = 20
INDEED_HOURS_OLD = 48          # look back 48h so a missed run doesn't lose jobs

# ============================================================
# EMIRATI-TARGETED ROLES
# ============================================================

# True  -> ONLY send jobs that are aimed at UAE nationals (Emiratization roles etc.)
# False -> send everything relevant, but rank Emirati-targeted roles first (🇦🇪)
EMIRATI_ONLY = False
EMIRATI_BONUS = 5

# Matched in the job TITLE (any of these).
EMIRATI_TITLE_KEYWORDS = [
    "emirati", "emiratis", "uae national", "uae nationals", "emiratization",
    "emiratisation", "national talent", "nationals only", "national graduate",
]
# Matched in the job DESCRIPTION. Kept stricter on purpose so that things like
# "Emirati cuisine" at a restaurant don't count as an Emiratization role.
EMIRATI_DESCRIPTION_KEYWORDS = [
    "uae national", "uae nationals", "emiratization", "emiratisation",
    "emirati national", "emirati nationals", "emirati candidate",
    "emirati candidates", "emirati graduate", "emirati graduates",
    "emiratis only", "open to emiratis", "for emiratis", "national talent",
    "nationals only", "local nationals",
]

# ============================================================
# RELEVANCE SCORING
# ============================================================
# Jobs are scored — only sent if score >= MIN_SCORE
MIN_SCORE = 1

# Only skip a job if it clearly asks for MORE than this many years of experience.
MAX_YEARS_EXPERIENCE = 2

# Salary floor (AED / month). 0 = OFF: nothing is filtered by pay, you negotiate in person.
# Listed salaries (when a board shows one, e.g. Indeed) are still displayed in the alert.
# Set a number (e.g. 8000) to hide listings whose stated AED salary is below it —
# listings with no salary are always kept either way.
MIN_SALARY_AED_MONTHLY = 0

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

# Sector words matched in the job TITLE only (+1 each) — keeps non-IT roles in play.
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
# TELEGRAM SAFETY
# ============================================================
TELEGRAM_MAX_CHARS = 3900    # Telegram limit is 4096, leave margin
TELEGRAM_SEND_DELAY_SEC = 1.1

# --- File to track seen jobs ---
SEEN_JOBS_FILE = "seen_jobs.json"

# --- Max jobs sent per run (best-scoring first; split over several Telegram messages) ---
# 3 runs a day x 40 = up to 120 alerts/day. Raise it if you want to see more of the backlog.
MAX_JOBS_PER_RUN = 40