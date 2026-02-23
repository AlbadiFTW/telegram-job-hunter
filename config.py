# ============================================================
# Job Scraper Configuration
# Tailored for: Abdul Rahman Albadi — Full Stack Engineer
# ============================================================

# --- Telegram Settings ---
# Get these by messaging @BotFather on Telegram
TELEGRAM_BOT_TOKEN= "your_actual_token"
TELEGRAM_CHAT_ID= "your_actual_chat_id"

# --- Search Keywords ---
# These are sent as search queries to each job board
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

# --- Location ---
LOCATION = "United Arab Emirates"

# --- Relevance Filter ---
# Jobs must contain at least ONE of these to pass filtering
# This avoids irrelevant results from broad keyword searches
REQUIRED_KEYWORDS = [
    "javascript", "typescript", "react", "next.js", "nextjs",
    "node", "node.js", "nodejs", "express", "python",
    "flask", "postgresql", "sql", "rest api", "api",
    "full stack", "fullstack", "full-stack", "backend",
    "frontend", "software engineer", "web developer",
    "junior", "graduate", "entry level", "fresh",
]

# --- Rejection Filter ---
# Jobs containing ANY of these will be skipped entirely
REJECTION_KEYWORDS = [
    "senior", "lead", "manager", "director", "head of",
    "10 years", "8 years", "7 years", "6 years", "5 years",
    "sap", "salesforce", "mainframe", "cobol", "fortran",
    "mechanical", "civil", "electrical", "accounting",
    "marketing", "sales", "driver", "cleaner",
]

# --- Salary Filter ---
# Skip jobs that mention very low salaries (optional)
MIN_SALARY_AED = 3000  # Skip if explicitly mentions below this

# --- File to track seen jobs ---
SEEN_JOBS_FILE = "seen_jobs.json"

# --- Max jobs per notification ---
MAX_JOBS_PER_MESSAGE = 10
