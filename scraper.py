import os
import requests
import json
import time
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

from config import (
    SEARCH_KEYWORDS, LOCATION, REQUIRED_KEYWORDS,
    REJECTION_KEYWORDS, SEEN_JOBS_FILE, MAX_JOBS_PER_MESSAGE,
    TELEGRAM_BOT_TOKEN as _CONFIG_TOKEN,
    TELEGRAM_CHAT_ID as _CONFIG_CHAT_ID,
)

# GitHub Actions reads from Repository Secrets
# Local development reads from .env file
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", _CONFIG_TOKEN)
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", _CONFIG_CHAT_ID)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}


# ============================================================
# SEEN JOBS TRACKER
# ============================================================

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)


def make_job_id(title, company):
    raw = f"{title.lower().strip()}{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


# ============================================================
# RELEVANCE FILTERING
# ============================================================

def is_relevant(title, description=""):
    text = f"{title} {description}".lower()

    for keyword in REJECTION_KEYWORDS:
        if keyword.lower() in text:
            return False

    for keyword in REQUIRED_KEYWORDS:
        if keyword.lower() in text:
            return True

    return False


# ============================================================
# LINKEDIN SCRAPER
# ============================================================

def scrape_linkedin(keyword):
    jobs = []
    query = keyword.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={query}&location=United%20Arab%20Emirates"
        f"&f_TPR=r86400&f_E=1%2C2"
    )

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [LinkedIn] Failed for '{keyword}' — status {response.status_code}")
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("div", {"class": "base-card"})

        for listing in listings[:20]:
            try:
                title_tag = listing.find("h3", {"class": "base-search-card__title"})
                company_tag = listing.find("h4", {"class": "base-search-card__subtitle"})
                location_tag = listing.find("span", {"class": "job-search-card__location"})
                link_tag = listing.find("a", {"class": "base-card__full-link"})

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                location = location_tag.get_text(strip=True) if location_tag else "UAE"
                link = link_tag["href"].split("?")[0]

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": link,
                        "source": "LinkedIn",
                        "id": make_job_id(title, company)
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"  [LinkedIn] Error: {e}")

    return jobs


# ============================================================
# WUZZUF SCRAPER
# ============================================================

def scrape_wuzzuf(keyword):
    jobs = []
    query = keyword.replace(" ", "+")
    url = f"https://wuzzuf.net/search/jobs/?q={query}&a=hpb"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [Wuzzuf] Failed for '{keyword}' — status {response.status_code}")
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("div", {"class": "css-1gatmva"})

        for listing in listings[:20]:
            try:
                title_tag = listing.find("h2", {"class": "css-m604qf"})
                company_tag = listing.find("a", {"class": "css-17s97q8"})
                location_tag = listing.find("span", {"class": "css-5wys0k"})
                link_tag = title_tag.find("a") if title_tag else None

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                location = location_tag.get_text(strip=True) if location_tag else "UAE"
                link = "https://wuzzuf.net" + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": link,
                        "source": "Wuzzuf",
                        "id": make_job_id(title, company)
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"  [Wuzzuf] Error: {e}")

    return jobs


# ============================================================
# TELEGRAM NOTIFICATIONS
# ============================================================

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[Telegram] Failed: {response.text}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")


def format_job_message(jobs, total_new):
    date_str = datetime.now().strftime("%d %b %Y")
    header = f"🚀 <b>Job Alert — {date_str}</b>\n"
    header += f"Found <b>{total_new} new jobs</b> matching your profile\n"
    header += "─" * 30 + "\n\n"

    body = ""
    for job in jobs[:MAX_JOBS_PER_MESSAGE]:
        body += f"💼 <b>{job['title']}</b>\n"
        body += f"🏢 {job['company']}\n"
        body += f"📍 {job['location']}\n"
        body += f"🌐 {job['source']}\n"
        body += f"🔗 <a href='{job['url']}'>Apply Now</a>\n"
        body += "\n"

    footer = ""
    if total_new > MAX_JOBS_PER_MESSAGE:
        footer = f"... and {total_new - MAX_JOBS_PER_MESSAGE} more jobs found today.\n"

    footer += "\n💪 Good luck Abdul Rahman!"

    return header + body + footer


def send_no_jobs_message():
    date_str = datetime.now().strftime("%d %b %Y")
    send_telegram_message(
        f"📭 <b>Job Alert — {date_str}</b>\n\n"
        "No new jobs found today matching your profile.\n"
        "Keep your applications going — new listings appear daily!"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"\n{'='*50}")
    print(f"Job Scraper Started — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*50}\n")

    seen_jobs = load_seen_jobs()
    all_jobs = []
    seen_ids = set()

    for keyword in SEARCH_KEYWORDS:
        print(f"Searching: '{keyword}'...")

        linkedin_jobs = scrape_linkedin(keyword)
        print(f"  [LinkedIn] Found {len(linkedin_jobs)} relevant listings")

        wuzzuf_jobs = scrape_wuzzuf(keyword)
        print(f"  [Wuzzuf] Found {len(wuzzuf_jobs)} relevant listings")

        for job in linkedin_jobs + wuzzuf_jobs:
            if job["id"] not in seen_jobs and job["id"] not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job["id"])

        time.sleep(2)

    print(f"\nTotal new jobs found: {len(all_jobs)}")

    if all_jobs:
        all_jobs.sort(key=lambda x: x["source"])
        message = format_job_message(all_jobs, len(all_jobs))
        send_telegram_message(message)
        print("[Telegram] Notification sent!")

        for job in all_jobs:
            seen_jobs.add(job["id"])
        save_seen_jobs(seen_jobs)

    else:
        send_no_jobs_message()
        print("[Telegram] No new jobs notification sent.")

    print("\nDone!")


if __name__ == "__main__":
    main()
