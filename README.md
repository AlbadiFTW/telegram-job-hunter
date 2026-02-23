# UAE Job Scraper 🚀

A Python job scraper that monitors **Bayt.com** and **LinkedIn** daily for UAE tech jobs and sends new listings directly to your **Telegram** — automatically, every morning at 7AM UAE time via GitHub Actions.

No server needed. Completely free to run.

## How It Works

1. GitHub Actions triggers the scraper every morning at 7AM UAE time
2. The scraper searches Bayt.com and LinkedIn for tech jobs in the UAE
3. Jobs are filtered by relevance — seniority, unrelated fields, and already-seen jobs are excluded
4. New matching jobs are sent to your Telegram with title, company, location, and apply link
5. Seen jobs are saved back to the repo so you never get duplicates

## Example Telegram Message

```
🚀 Job Alert — 23 Feb 2026
Found 8 new jobs matching your profile
──────────────────────────────

💼 Junior Software Engineer
🏢 Noon
📍 Dubai, UAE
🌐 LinkedIn
🔗 Apply Now

💼 Full Stack Developer
🏢 Careem
📍 Abu Dhabi, UAE
🌐 Bayt.com
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
2. Install dependencies: `pip install -r requirements.txt`
3. Edit `setup_telegram.py` — paste your bot token
4. Run: `python setup_telegram.py`
5. Copy the **Chat ID** from the output

### Step 3 — Configure

Edit `config.py`:
```python
TELEGRAM_BOT_TOKEN = "your_token_here"
TELEGRAM_CHAT_ID = "your_chat_id_here"
```

### Step 4 — Test Locally

```bash
pip install -r requirements.txt
python scraper.py
```

You should receive a Telegram message within seconds.

### Step 5 — Deploy to GitHub Actions (Free Automation)

1. Push this repo to GitHub
2. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
3. Add two secrets:
   - `TELEGRAM_BOT_TOKEN` — your bot token
   - `TELEGRAM_CHAT_ID` — your chat ID
4. Go to **Actions** tab → enable workflows
5. Click **Run workflow** to test it manually

From now on it runs automatically every day at 7AM UAE time.

## Customisation

### Change search keywords (`config.py`)
```python
SEARCH_KEYWORDS = [
    "full stack developer",
    "React developer",
    # Add or remove as needed
]
```

### Change filtering (`config.py`)
```python
# Jobs must contain at least one of these
REQUIRED_KEYWORDS = ["react", "node", "python", ...]

# Jobs containing any of these are skipped
REJECTION_KEYWORDS = ["senior", "10 years", ...]
```

### Change schedule (`.github/workflows/daily_scrape.yml`)
```yaml
# Currently: 7AM UAE time (03:00 UTC)
- cron: "0 3 * * *"

# For 9AM UAE time:
- cron: "0 5 * * *"
```

## Project Structure

```
job-scraper/
├── scraper.py              # Main scraper — Bayt + LinkedIn
├── config.py               # Keywords, filters, settings
├── setup_telegram.py       # One-time helper to get chat ID
├── seen_jobs.json          # Tracks seen jobs (auto-updated)
├── requirements.txt        # Python dependencies
└── .github/
    └── workflows/
        └── daily_scrape.yml # GitHub Actions automation
```

## Tech Stack

- **Python** — scraping and logic
- **BeautifulSoup** — HTML parsing
- **Requests** — HTTP calls
- **Telegram Bot API** — notifications
- **GitHub Actions** — free daily automation

```
## Customising Keywords For Your Profile

Edit `config.py` to tailor the scraper to your specific field:

### For Frontend Developers
```python
SEARCH_KEYWORDS = ["React developer", "frontend developer", "Vue.js developer", "UI developer"]
```

### For Backend Developers
```python
SEARCH_KEYWORDS = ["backend developer", "Node.js developer", "Python developer", "API developer"]
```

### For Data/ML Engineers
```python
SEARCH_KEYWORDS = ["data engineer", "machine learning engineer", "data scientist", "AI engineer"]
```

### For Any Field
Just replace the keywords with whatever role you're targeting. The scraper will search each keyword separately and combine the results.

## Troubleshooting

**Bot not sending messages**
- Make sure you sent your bot a message before running `setup_telegram.py`
- Double check your token and chat ID in `config.py`
- Verify your bot token has no extra spaces

**lxml install fails on Windows**
- lxml isn't required — remove it from `requirements.txt` and run `pip install requests beautifulsoup4` instead

**No jobs found**
- Bayt and LinkedIn occasionally change their HTML structure which breaks the scraper
- Open an issue on GitHub and I'll push a fix
- You can test manually by running `python scraper.py` locally

**GitHub Actions not triggering**
- Go to Actions tab and make sure workflows are enabled
- Use the "Run workflow" button to trigger manually and check the logs
- Verify your secrets are added correctly in Settings → Secrets

**Duplicate jobs appearing**
- Make sure `seen_jobs.json` is being committed back to the repo by GitHub Actions
- Check the Actions log for the "Commit updated seen_jobs.json" step

```
## License

MIT
