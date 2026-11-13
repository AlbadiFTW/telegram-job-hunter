# UAE Job Scraper 🚀

A Python job scraper that monitors **LinkedIn** for **Emiratization jobs in Abu Dhabi and Al Ain** (roles open to UAE nationals, needing 0–3 years of experience, across all sectors — hospitality, customer service, admin, business, tech and more) and sends new listings directly to your **Telegram**, automatically, 3 times daily (7AM, 11AM, 5PM UAE time) via GitHub Actions.

No server needed. Completely free to run.

## New Additions

- **Job Application Tracker Bot** — log applications and track interview/rejection stats via Telegram commands.
- **Weekly Summary** — sends a weekly snapshot of applications and outcomes.

## How It Works

1. GitHub Actions triggers the scraper 3 times daily at 7AM, 11AM, and 5PM UAE time
2. The scraper searches LinkedIn for Emirati-focused keywords in Al Ain and Abu Dhabi, then opens each promising job to read the full description
3. A job is sent only if it is in Abu Dhabi/Al Ain, is aimed at UAE nationals, and asks for 3 years of experience or less. Senior roles, scams, low-pay roles and already-seen jobs are excluded; Al Ain jobs are ranked first
4. New matching jobs are sent to your Telegram with title, company, location, and apply link
5. Seen jobs are saved back to the repo so you never get duplicates

## Example Telegram Message

```
🚀 Job Alert — 24 Feb 2026
Found 6 new jobs matching your profile
──────────────────────────────

💼 Junior Software Engineer
🏢 Noon
📍 Dubai, UAE
🌐 LinkedIn
🔗 Apply Now

💼 Full Stack Developer
🏢 Careem
📍 Abu Dhabi, UAE
🌐 LinkedIn
🔗 Apply Now
...
```

## Setup (10 minutes)

### Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the **bot token** BotFather gives you (looks like `123456:ABCdef...`)

### Step 2 — Get Your Chat ID

1. Send your new bot any message (e.g. "hello")
2. Install dependencies: `pip install requests beautifulsoup4 python-dotenv`
3. Edit `setup_telegram.py` — paste your bot token
4. Run: `python setup_telegram.py`
5. Copy the **Chat ID** from the output

### Step 3 — Configure Locally

Create a `.env` file in the project root (never committed to GitHub):
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Keep `config.py` with placeholders — the scraper reads from `.env` automatically and falls back to `config.py` values if env vars are missing.

### Step 4 — Test Locally

```bash
pip install -r requirements.txt
python scraper.py
```

You should receive a Telegram message within a minute.

### Step 5 — Deploy to GitHub Actions (Free Automation)

1. Push this repo to GitHub
2. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
3. Under **Repository secrets** add:
   - `TELEGRAM_BOT_TOKEN` — your bot token (no quotes)
   - `TELEGRAM_CHAT_ID` — your chat ID (no quotes)
4. Go to **Actions** tab → enable workflows
5. Click **Run workflow** to test manually

From now on it runs automatically 3 times daily — no server, no cost.

## Optional Tools

### Application Tracker Bot (Telegram)

Run locally:
```bash
python bot.py
```

Commands:
- `/applied <company> <role>`
- `/interview <company>`
- `/rejected <company>`
- `/offer <company>`
- `/stats`
- `/list`

Data is saved in `applications.json`.

### Weekly Summary

Run manually:
```bash
python weekly_summary.py
```

Uses `applications.json` to generate a weekly Telegram summary.

## Troubleshooting

**Bot not sending messages**
- Make sure you sent your bot a message before running `setup_telegram.py`
- Double check your token and chat ID have no quotes or extra spaces in GitHub Secrets
- Secrets go under Settings → Secrets and variables → Actions → **Repository secrets** (not Environments)

**lxml install fails on Windows**
- Remove `lxml` from `requirements.txt` and run `pip install requests beautifulsoup4 python-dotenv` instead

**No jobs found**
- LinkedIn occasionally changes its HTML — open an issue and I'll push a fix
- Test manually by running `python scraper.py` locally

**Duplicate jobs appearing**
- Make sure `seen_jobs.json` is being committed back by GitHub Actions
- Check the Actions log for the "Commit updated seen_jobs.json" step

**Want to reset and resend all current jobs?**
```bash
python -c "import json; open('seen_jobs.json', 'w').write('[]')"
git add seen_jobs.json
git commit -m "fix: reset seen jobs"
git push
```

## Customising Keywords For Your Profile

Edit `config.py` to tailor the scraper to your field:

### For Frontend Developers
```python
SEARCH_KEYWORDS = ["React developer", "frontend developer", "Vue.js developer"]
```

### For Backend Developers
```python
SEARCH_KEYWORDS = ["backend developer", "Node.js developer", "Python developer"]
```

### For Data/ML Engineers
```python
SEARCH_KEYWORDS = ["data engineer", "machine learning engineer", "data scientist"]
```

### Change Schedule
Edit `.github/workflows/daily_scrape.yml`:
```yaml
# 7AM, 11AM, 5PM UAE time (UTC+4)
- cron: "0 3 * * *"
- cron: "0 7 * * *"
- cron: "0 13 * * *"
```

## Project Structure

```
telegram-job-hunter/
├── scraper.py              # Main scraper — LinkedIn (Bayt/GulfTalent/Dubizzle available but off)
├── config.py               # Keywords, filters, settings
├── setup_telegram.py       # One-time helper to get chat ID
├── bot.py                  # Telegram bot for application tracking
├── weekly_summary.py       # Weekly application summary sender
├── applications.json       # Tracked applications (auto-updated)
├── seen_jobs.json          # Tracks seen jobs (auto-updated by GitHub Actions)
├── requirements.txt        # Python dependencies
├── .env                    # Your secrets — local only, never committed
├── .gitignore              # Keeps .env off GitHub
└── .github/
    └── workflows/
        └── daily_scrape.yml # GitHub Actions automation
```

## Tech Stack

- **Python** — scraping and logic
- **BeautifulSoup** — HTML parsing
- **Requests** — HTTP calls
- **Telegram Bot API** — notifications
- **GitHub Actions** — free scheduled automation

## License

MIT

## Configuring the scraper (`config.py`)

| Setting | What it does |
|---|---|
| `LOCATIONS` / `ALLOWED_LOCATION_MARKERS` | Where to search, and which location texts are accepted (Abu Dhabi emirate incl. Al Ain only) |
| `PRIORITY_LOCATIONS` | Al Ain jobs get a ranking bonus (⭐) |
| `EMIRATI_ONLY` | `True` = only roles aimed at UAE nationals (checked in the full job description); `False` = everything, Emirati roles ranked first |
| `MAX_YEARS_EXPERIENCE` | Skip jobs asking for more than this many years (default 3). Jobs that don't state years are kept |
| `ENABLED_SECTORS` / `KEYWORDS_BY_SECTOR` | The Emirati-focused LinkedIn searches; edit or add keywords |
| `LINKEDIN_TIME_WINDOW` | `r86400` = last 24h. Use `r604800` for one run to catch up on the past week |
| `MAX_DETAIL_FETCHES_PER_RUN` | How many job pages to open per run (the slow part) |
| `MIN_SCORE`, `MAX_JOBS_PER_RUN` | How picky the seniority/relevance filter is, and how many jobs are sent per run |
| `PREFERRED_COMPANIES` | Employers that get a ranking bonus |
| `SEND_EMPTY_NOTICE` | `True` = also send a message when a run finds nothing |
| `ENABLED_SOURCES` | Bayt / GulfTalent / Dubizzle can be switched on, but they only show job titles, so Emiratization roles are only recognised if the title says so |
| `REJECT_*_KEYWORDS` | Titles / text that are always skipped |

**Why no Indeed or Naukrigulf?** Indeed was removed on request. Naukrigulf can't be scraped with a plain script: its pages are rendered by JavaScript and its data endpoint sits behind bot protection (existing scrapers rely on paid residential proxies). Set up a free email alert on naukrigulf.com for "Emirati" in Abu Dhabi / Al Ain instead.

Run the offline sanity checks for the filters with `python tests/test_filters.py`.