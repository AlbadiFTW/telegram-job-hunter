import os
import requests
import json
import time
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

from config import (
    SEARCH_KEYWORDS, LOCATIONS,
    SCORE_BOOST_KEYWORDS, SCORE_PENALTY_KEYWORDS,
    REJECTION_KEYWORDS, SEEN_JOBS_FILE, MAX_JOBS_PER_MESSAGE,
    TELEGRAM_MAX_CHARS, TELEGRAM_SEND_DELAY_SEC, MIN_SCORE,
    TELEGRAM_BOT_TOKEN as _CONFIG_TOKEN,
    TELEGRAM_CHAT_ID as _CONFIG_CHAT_ID,
)

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
# RELEVANCE SCORING
# ============================================================

def score_job(title, description=""):
    text = f"{title} {description}".lower()

    for keyword in REJECTION_KEYWORDS:
        if keyword.lower() in text:
            return -99

    score = 0

    for keyword, boost in SCORE_BOOST_KEYWORDS:
        if keyword.lower() in text:
            score += boost

    for keyword, penalty in SCORE_PENALTY_KEYWORDS:
        if keyword.lower() in text:
            score += penalty

    return score


def is_relevant(title, description=""):
    return score_job(title, description) >= MIN_SCORE


# ============================================================
# LINKEDIN SCRAPER — removed experience filter to catch more roles
# ============================================================

def scrape_linkedin(keyword, location="United Arab Emirates"):
    jobs = []
    query = keyword.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    # Removed f_E=1%2C2 (entry level filter) — catches more junior roles
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={query}&location={loc}&f_TPR=r86400"
    )

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [LinkedIn] Failed '{keyword}' in {location} — {response.status_code}")
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
                loc_text = location_tag.get_text(strip=True) if location_tag else location
                link = link_tag["href"].split("?")[0]

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc_text,
                        "url": link,
                        "source": "LinkedIn",
                        "score": score_job(title),
                        "id": make_job_id(title, company)
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"  [LinkedIn] Error: {e}")

    return jobs


# ============================================================
# BAYT SCRAPER
# ============================================================

def scrape_bayt(keyword):
    jobs = []
    query = keyword.strip().lower().replace(" ", "-")
    url = f"https://www.bayt.com/en/uae/jobs/{query}-jobs/"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [Bayt] Failed '{keyword}' — {response.status_code}")
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("li", {"class": lambda c: c and "has-pointer-d" in c})

        for listing in listings[:20]:
            try:
                title_tag = listing.find("h2", {"class": "m0 t-regular"})
                company_tag = listing.find("b", {"class": "t-default"})
                location_tag = listing.find("span", {"class": "t-mute"})
                link_tag = listing.find("a", href=True)

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                location = location_tag.get_text(strip=True) if location_tag else "UAE"
                link = "https://www.bayt.com" + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": link,
                        "source": "Bayt",
                        "score": score_job(title),
                        "id": make_job_id(title, company)
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"  [Bayt] Error: {e}")

    return jobs


# ============================================================
# GULFTALEN SCRAPER
# ============================================================

def scrape_gulftalen(keyword):
    jobs = []
    query = keyword.replace(" ", "+")
    url = f"https://www.gulftalen.com/en/jobs/?search={query}&country=UAE"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [GulfTalent] Failed '{keyword}' — {response.status_code}")
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("div", {"class": "job-item"})

        for listing in listings[:20]:
            try:
                title_tag = listing.find("h3")
                company_tag = listing.find("span", {"class": "company"})
                location_tag = listing.find("span", {"class": "location"})
                link_tag = listing.find("a", href=True)

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                location = location_tag.get_text(strip=True) if location_tag else "UAE"
                href = link_tag["href"]
                link = "https://www.gulftalen.com" + href if href.startswith("/") else href

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": link,
                        "source": "GulfTalent",
                        "score": score_job(title),
                        "id": make_job_id(title, company)
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"  [GulfTalent] Error: {e}")

    return jobs


# ============================================================
# DUBIZZLE SCRAPER
# ============================================================

def scrape_dubizzle(keyword):
    jobs = []
    query = keyword.replace(" ", "%20")
    url = f"https://uae.dubizzle.com/jobs/?search={query}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [Dubizzle] Failed '{keyword}' — {response.status_code}")
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("article")

        for listing in listings[:20]:
            try:
                title_tag = listing.find("h2") or listing.find("h3")
                company_tag = listing.find("span", {"class": lambda c: c and "company" in str(c).lower()})
                location_tag = listing.find("span", {"class": lambda c: c and "location" in str(c).lower()})
                link_tag = listing.find("a", href=True)

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                location = location_tag.get_text(strip=True) if location_tag else "UAE"
                href = link_tag["href"]
                link = "https://uae.dubizzle.com" + href if href.startswith("/") else href

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": link,
                        "source": "Dubizzle",
                        "score": score_job(title),
                        "id": make_job_id(title, company)
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"  [Dubizzle] Error: {e}")

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
            print(f"  [Wuzzuf] Failed '{keyword}' — {response.status_code}")
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
                loc_text = location_tag.get_text(strip=True) if location_tag else "UAE"
                link = "https://wuzzuf.net" + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]

                if is_relevant(title):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc_text,
                        "url": link,
                        "source": "Wuzzuf",
                        "score": score_job(title),
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


def send_jobs_in_chunks(jobs, total_new):
    date_str = datetime.now().strftime("%d %b %Y")
    header = (
        f"🚀 <b>Job Alert — {date_str}</b>\n"
        f"Found <b>{total_new} new jobs</b> matching your profile\n"
        f"{'─' * 30}\n\n"
    )

    current_message = header

    for job in jobs:
        job_text = (
            f"💼 <b>{job['title']}</b>\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"🌐 {job['source']}\n"
            f"🔗 <a href='{job['url']}'>Apply Now</a>\n\n"
        )

        if len(current_message) + len(job_text) > TELEGRAM_MAX_CHARS:
            send_telegram_message(current_message)
            time.sleep(TELEGRAM_SEND_DELAY_SEC)
            current_message = "🚀 <b>Job Alert (continued)</b>\n\n"

        current_message += job_text

    current_message += "\n💪 Good luck Abdul Rahman!"
    send_telegram_message(current_message)


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

        for location in LOCATIONS:
            linkedin_jobs = scrape_linkedin(keyword, location)
            print(f"  [LinkedIn] '{location}' — {len(linkedin_jobs)} listings")
            for job in linkedin_jobs:
                if job["id"] not in seen_jobs and job["id"] not in seen_ids:
                    all_jobs.append(job)
                    seen_ids.add(job["id"])
            time.sleep(3)

        bayt_jobs = scrape_bayt(keyword)
        print(f"  [Bayt] Found {len(bayt_jobs)} listings")
        for job in bayt_jobs:
            if job["id"] not in seen_jobs and job["id"] not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job["id"])

        gulftalen_jobs = scrape_gulftalen(keyword)
        print(f"  [GulfTalent] Found {len(gulftalen_jobs)} listings")
        for job in gulftalen_jobs:
            if job["id"] not in seen_jobs and job["id"] not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job["id"])

        dubizzle_jobs = scrape_dubizzle(keyword)
        print(f"  [Dubizzle] Found {len(dubizzle_jobs)} listings")
        for job in dubizzle_jobs:
            if job["id"] not in seen_jobs and job["id"] not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job["id"])

        wuzzuf_jobs = scrape_wuzzuf(keyword)
        print(f"  [Wuzzuf] Found {len(wuzzuf_jobs)} listings")
        for job in wuzzuf_jobs:
            if job["id"] not in seen_jobs and job["id"] not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job["id"])

        time.sleep(2)

    all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)

    print(f"\nTotal new jobs found: {len(all_jobs)}")

    if all_jobs:
        send_jobs_in_chunks(all_jobs[:MAX_JOBS_PER_MESSAGE * 2], len(all_jobs))
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