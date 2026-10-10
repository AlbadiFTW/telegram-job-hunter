# UAE Job Scraper 🚀

A Python job scraper that monitors **LinkedIn, Indeed, Bayt, GulfTalent and Dubizzle** for **UAE-only** jobs across **all sectors** (hospitality, customer service, admin, business, tech, and more) — with **Al Ain** as a priority location and **Emirati-targeted roles** flagged 🇦🇪 — and sends new listings directly to your **Telegram**, automatically, 3 times daily (7AM, 11AM, 5PM UAE time) via GitHub Actions.

No server needed. Completely free to run.

## New Additions

- **Job Application Tracker Bot** — log applications and track interview/rejection stats via Telegram commands.
- **Daily Interview Questions** — sends one technical and one behavioural question each morning.
- **Weekly Summary** — sends a weekly snapshot of applications and outcomes.

## How It Works

1. GitHub Actions triggers the scraper 3 times daily at 7AM, 11AM, and 5PM UAE time
2. The scraper searches every configured source for every keyword in Al Ain and across the UAE
3. Jobs are filtered and ranked — non-UAE locations, senior roles, scams, low-pay roles and already-seen jobs are excluded; Al Ain jobs and Emirati-targeted roles are ranked first
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
🌐 Indeed
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

### Daily Interview Questions

Run manually:
```bash
python daily_question.py
```

Questions are stored in `questions.py`. Seen questions are tracked in `seen_questions.json`.

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
- LinkedIn and Wuzzuf occasionally change their HTML — open an issue and I'll push a fix
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
├── scraper.py              # Main scraper — LinkedIn + Wuzzuf
├── config.py               # Keywords, filters, settings
├── setup_telegram.py       # One-time helper to get chat ID
├── bot.py                  # Telegram bot for application tracking
├── daily_question.py       # Sends daily interview questions
├── questions.py            # Question bank for daily questions
├── weekly_summary.py       # Weekly application summary sender
├── applications.json       # Tracked applications (auto-updated)
├── seen_jobs.json          # Tracks seen jobs (auto-updated by GitHub Actions)
├── seen_questions.json     # Tracks seen interview questions
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
| `LOCATIONS` / `PRIORITY_LOCATIONS` | Where to search; Al Ain jobs get a score bonus |
| `ENABLED_SECTORS` / `KEYWORDS_BY_SECTOR` | Which sectors (emirati, hospitality, office_admin_hr, business, tech) to search; edit or add keywords |
| `ENABLED_SOURCES` | Turn individual job boards on/off |
| `EMIRATI_ONLY` | `True` = only send roles aimed at UAE nationals; `False` = send everything, ranked with Emirati roles first |
| `PREFERRED_COMPANIES` | Employers that get a score bonus |
| `MAX_YEARS_EXPERIENCE`, `MIN_SALARY_AED_MONTHLY` | Experience cap, and an optional salary floor (`0` = off; listed salaries are still shown) |
| `REJECT_*_KEYWORDS` | Titles / text that are always skipped |

Indeed is scraped through [`python-jobspy`](https://github.com/speedyapply/JobSpy), since Indeed blocks plain `requests` calls.

Run the offline sanity checks for the filters with `python tests/test_filters.py`.