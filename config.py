# ============================================================
# Job Scraper Configuration
# Tailored for: Abdul Rahman Albadi — Full Stack Engineer
# ============================================================

# --- Telegram Settings ---
# Get these by messaging @BotFather on Telegram
# Keep placeholders here — real values go in .env file
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# --- Search Keywords ---
SEARCH_KEYWORDS = [
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
]

# --- Locations to search ---
# Scraper will search each keyword in each location
LOCATIONS = [
    "United Arab Emirates",
    "Oman",
    "Qatar",
    "Saudi Arabia",
    ]

# --- Relevance Scoring ---
# Jobs are scored — only sent if score >= MIN_SCORE
MIN_SCORE = 1

# Keywords that boost the score (job is more likely relevant)
SCORE_BOOST_KEYWORDS = [
    ("junior", 2), ("graduate", 2), ("entry level", 2), ("entry-level", 2),
    ("fresh", 2), ("0-2 years", 2), ("0-1 year", 2), ("trainee", 2),
    ("react", 1), ("next.js", 2), ("nextjs", 1), ("node", 1),
    ("node.js", 1), ("nodejs", 1), ("python", 1), ("typescript", 2),
    ("javascript", 1), ("full stack", 1), ("fullstack", 1),
    ("express", 1), ("postgresql", 1), ("prisma", 2), ("tailwind", 1),
    ("rest api", 1), ("jwt", 1), ("socket.io", 2),
]

# Keywords that lower the score (job is less likely relevant)
SCORE_PENALTY_KEYWORDS = [
    ("senior", -3), ("sr.", -3), ("sr ", -3), ("lead", -3),
    ("principal", -3), ("architect", -3), ("head of", -3),
    ("director", -3), ("manager", -3), ("vp ", -3),
    ("vice president", -3), ("10 years", -3), ("8 years", -3),
    ("7 years", -3), ("6 years", -3), ("5 years", -3),
]

# Hard reject — skip immediately regardless of score
REJECTION_KEYWORDS = [
    "c++", "embedded", "sap", "salesforce", "mainframe", "cobol",
    "mechanical", "civil", "electrical", "accounting",
    "marketing", "sales", "driver", "cleaner", "secretary",
    "commission", "telesales", "door to door", "odoo functional",
    "emirati", "uae nationals", "national talent", "nationals only",
    "php", "wordpress", "laravel",
]

# --- Telegram Safety ---
TELEGRAM_MAX_CHARS = 3900    # Telegram limit is 4096, leave margin
TELEGRAM_SEND_DELAY_SEC = 1.1

# --- File to track seen jobs ---
SEEN_JOBS_FILE = "seen_jobs.json"

# --- Max jobs per notification message ---
MAX_JOBS_PER_MESSAGE = 10