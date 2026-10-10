import os
import re
import html
import json
import time
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

from config import (
    SEARCH_KEYWORDS, LOCATIONS, ENABLED_SOURCES,
    PRIORITY_LOCATIONS, PRIORITY_LOCATION_BONUS,
    PREFERRED_COMPANIES, PREFERRED_COMPANY_BONUS,
    UAE_LOCATION_MARKERS, FOREIGN_LOCATION_MARKERS,
    EMIRATI_ONLY, EMIRATI_BONUS, EMIRATI_TITLE_KEYWORDS, EMIRATI_DESCRIPTION_KEYWORDS,
    SCORE_BOOST_KEYWORDS, SCORE_PENALTY_KEYWORDS, SECTOR_TITLE_KEYWORDS,
    REJECT_TITLE_KEYWORDS, REJECT_ANYWHERE_KEYWORDS,
    MAX_YEARS_EXPERIENCE, MIN_SALARY_AED_MONTHLY,
    INDEED_RESULTS_WANTED, INDEED_HOURS_OLD,
    SEEN_JOBS_FILE, MAX_JOBS_PER_RUN,
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
# HTTP HELPER (retries on rate-limits / server errors)
# ============================================================

def http_get(url, retries=2):
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
        except requests.RequestException as e:
            print(f"  [HTTP] {e}")
            time.sleep(2)
            continue
        if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(5 * (attempt + 1))
            continue
        return response
    return None


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
        json.dump(sorted(seen), f)


def make_job_id(title, company):
    raw = f"{title.lower().strip()}{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


# ============================================================
# TEXT MATCHING HELPERS
# ============================================================

@lru_cache(maxsize=None)
def _pattern(phrase):
    # whole-word / whole-phrase match, so "sap" doesn't hit "Sapphire"
    return re.compile(r"(?<![a-z0-9])" + re.escape(phrase.strip().lower()) + r"(?![a-z0-9])")


def has(text, phrase):
    return _pattern(phrase).search(text) is not None


def has_any(text, phrases):
    return any(has(text, p) for p in phrases)


_NON_EMIRATI_RE = re.compile(r"\bnon[\s-]?(emirati|uae national)s?\b")
_YEARS_RE = re.compile(r"(\d{1,2})\s*(?:\+|\s*(?:-|–|—|to)\s*\d{1,2}\s*\+?)?\s*(?:years?|yrs?)\b")


def min_years_required(text):
    """Smallest 'N years' figure that sits next to the word 'experience', or None."""
    found = []
    for m in _YEARS_RE.finditer(text):
        window = text[max(0, m.start() - 60): m.end() + 60]
        if "experience" in window:
            found.append(int(m.group(1)))
    return min(found) if found else None


# ============================================================
# LOCATION / SALARY FILTERS
# ============================================================

def is_uae_location(location):
    """UAE-only filter. All sources are searched with a UAE scope already, so an
    unknown/empty location is accepted — but anything naming another country is not."""
    loc = (location or "").lower()
    if has_any(loc, UAE_LOCATION_MARKERS):
        return True
    if has_any(loc, FOREIGN_LOCATION_MARKERS):
        return False
    return True


def _s(x, default=""):
    """str() that turns None / NaN (pandas) into a default instead of the text 'nan'."""
    if x is None or (isinstance(x, float) and x != x):
        return default
    return str(x)


def _num(x):
    try:
        v = float(x)
        return v if v == v else None   # NaN -> None
    except (TypeError, ValueError):
        return None


def monthly_aed(amount, interval, currency):
    """Convert a listed salary to AED/month. Returns None if not convertible."""
    amount = _num(amount)
    if amount is None or (currency and str(currency).upper() != "AED"):
        return None
    interval = str(interval or "").lower()
    factors = {"monthly": 1, "yearly": 1 / 12, "weekly": 4.33, "daily": 22, "hourly": 22 * 8}
    return amount * factors[interval] if interval in factors else None


def salary_below_floor(job):
    if not MIN_SALARY_AED_MONTHLY:
        return False
    top = monthly_aed(job.get("max_amount") or job.get("min_amount"),
                      job.get("interval"), job.get("currency"))
    return top is not None and top < MIN_SALARY_AED_MONTHLY


def salary_text(job):
    lo, hi = _num(job.get("min_amount")), _num(job.get("max_amount"))
    if lo is None and hi is None:
        return ""
    cur = job.get("currency") or ""
    rng = f"{lo:,.0f}–{hi:,.0f}" if lo and hi and lo != hi else f"{(hi or lo):,.0f}"
    return f"{rng} {cur} / {job.get('interval') or '?'}".strip()


# ============================================================
# RELEVANCE SCORING
# ============================================================

def evaluate_job(raw):
    """Returns the job dict enriched with score/flags, or None if it should be skipped."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    description = raw.get("description") or ""
    company = raw.get("company") or "Unknown"
    location = raw.get("location") or "UAE"

    title_l = title.lower()
    text = f"{title} {description}".lower()

    # --- hard rejects ---
    if not is_uae_location(location):
        return None
    if has_any(title_l, REJECT_TITLE_KEYWORDS) or has_any(text, REJECT_ANYWHERE_KEYWORDS):
        return None
    if salary_below_floor(raw):
        return None

    years = min_years_required(text)
    if years is not None and years > MAX_YEARS_EXPERIENCE:
        return None

    # --- Emirati-targeted roles ---
    title_nat = _NON_EMIRATI_RE.sub(" ", title_l)
    desc_nat = _NON_EMIRATI_RE.sub(" ", description.lower())
    emirati = has_any(title_nat, EMIRATI_TITLE_KEYWORDS) or has_any(desc_nat, EMIRATI_DESCRIPTION_KEYWORDS)
    if EMIRATI_ONLY and not emirati:
        return None

    # --- score ---
    score = 0
    score += sum(b for kw, b in SCORE_BOOST_KEYWORDS if has(text, kw))
    score += sum(1 for kw in SECTOR_TITLE_KEYWORDS if has(title_l, kw))
    score += sum(p for kw, p in SCORE_PENALTY_KEYWORDS if has(title_l, kw))
    if years == MAX_YEARS_EXPERIENCE:
        score -= 1
    if emirati:
        score += EMIRATI_BONUS

    loc_l = f"{location} {title}".lower()
    al_ain = any(p in loc_l for p in PRIORITY_LOCATIONS)
    if al_ain:
        score += PRIORITY_LOCATION_BONUS
    if has_any(company.lower(), PREFERRED_COMPANIES):
        score += PREFERRED_COMPANY_BONUS

    if score < MIN_SCORE:
        return None

    return {
        "title": title,
        "company": company,
        "location": location,
        "url": raw.get("url", ""),
        "source": raw.get("source", ""),
        "score": score,
        "emirati": emirati,
        "al_ain": al_ain,
        "salary": salary_text(raw),
        "id": make_job_id(title, company),
    }


# ============================================================
# LINKEDIN SCRAPER
# ============================================================

def scrape_linkedin(keyword, location):
    jobs = []
    query = keyword.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={query}&location={loc}&f_TPR=r86400"
    )

    response = http_get(url)
    if response is None or response.status_code != 200:
        code = response.status_code if response is not None else "no response"
        print(f"  [LinkedIn] Failed '{keyword}' in {location} — {code}")
        return jobs

    soup = BeautifulSoup(response.text, "html.parser")
    for listing in soup.find_all("div", {"class": "base-card"})[:25]:
        try:
            title_tag = listing.find("h3", {"class": "base-search-card__title"})
            company_tag = listing.find("h4", {"class": "base-search-card__subtitle"})
            location_tag = listing.find("span", {"class": "job-search-card__location"})
            link_tag = listing.find("a", {"class": "base-card__full-link"})
            if not title_tag or not link_tag:
                continue
            jobs.append({
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": location_tag.get_text(strip=True) if location_tag else "",
                "url": link_tag["href"].split("?")[0],
                "source": "LinkedIn",
            })
        except Exception:
            continue
    return jobs


# ============================================================
# INDEED SCRAPER (via python-jobspy — Indeed blocks plain requests)
# ============================================================

def scrape_indeed(keyword, location):
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  [Indeed] python-jobspy not installed — skipping (pip install python-jobspy)")
        return []

    short_location = location.split(",")[0].strip()   # "Al Ain, Abu Dhabi, ..." -> "Al Ain"
    try:
        df = scrape_jobs(
            site_name=["indeed"],
            search_term=keyword,
            location=short_location,
            country_indeed="UAE",
            results_wanted=INDEED_RESULTS_WANTED,
            hours_old=INDEED_HOURS_OLD,
            description_format="markdown",
            verbose=0,
        )
    except Exception as e:
        print(f"  [Indeed] Error '{keyword}' in {short_location}: {e}")
        return []

    jobs = []
    for row in df.to_dict("records"):
        jobs.append({
            "title": _s(row.get("title")),
            "company": _s(row.get("company"), "Unknown"),
            "location": _s(row.get("location")),
            "url": _s(row.get("job_url")),
            "description": _s(row.get("description")),
            "min_amount": row.get("min_amount"),
            "max_amount": row.get("max_amount"),
            "interval": row.get("interval"),
            "currency": row.get("currency"),
            "source": "Indeed",
        })
    return jobs


# ============================================================
# BAYT SCRAPER
# ============================================================

def scrape_bayt(keyword, location):
    jobs = []
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
    if location.lower().startswith("al ain"):
        url = f"https://www.bayt.com/en/uae/jobs/{slug}-jobs-in-al-ain/"
    else:
        url = f"https://www.bayt.com/en/uae/jobs/{slug}-jobs/"

    response = http_get(url)
    if response is None or response.status_code != 200:
        code = response.status_code if response is not None else "no response"
        print(f"  [Bayt] Failed '{keyword}' ({location.split(',')[0]}) — {code}")
        return jobs

    soup = BeautifulSoup(response.text, "html.parser")
    listings = soup.find_all("li", {"class": lambda c: c and "has-pointer-d" in c})
    for listing in listings[:25]:
        try:
            title_tag = listing.find("h2", {"class": "m0 t-regular"})
            company_tag = listing.find("b", {"class": "t-default"})
            location_tag = listing.find("span", {"class": "t-mute"})
            link_tag = listing.find("a", href=True)
            if not title_tag or not link_tag:
                continue
            href = link_tag["href"]
            jobs.append({
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": location_tag.get_text(strip=True) if location_tag else "",
                "url": "https://www.bayt.com" + href if href.startswith("/") else href,
                "source": "Bayt",
            })
        except Exception:
            continue
    return jobs


# ============================================================
# GULFTALENT SCRAPER
# ============================================================

def scrape_gulftalent(keyword):
    jobs = []
    query = keyword.replace(" ", "+")
    url = f"https://www.gulftalent.com/uae/jobs/search/?search_text={query}"

    response = http_get(url)
    if response is None or response.status_code != 200:
        code = response.status_code if response is not None else "no response"
        print(f"  [GulfTalent] Failed '{keyword}' — {code}")
        return jobs

    soup = BeautifulSoup(response.text, "html.parser")
    for listing in soup.find_all("div", {"class": "job-item"})[:25]:
        try:
            title_tag = listing.find("h3")
            company_tag = listing.find("span", {"class": "company"})
            location_tag = listing.find("span", {"class": "location"})
            link_tag = listing.find("a", href=True)
            if not title_tag or not link_tag:
                continue
            href = link_tag["href"]
            jobs.append({
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": location_tag.get_text(strip=True) if location_tag else "",
                # NOTE: the old code had a typo here ("gulftalen.com") which broke every link
                "url": "https://www.gulftalent.com" + href if href.startswith("/") else href,
                "source": "GulfTalent",
            })
        except Exception:
            continue
    return jobs


# ============================================================
# DUBIZZLE SCRAPER
# ============================================================

def scrape_dubizzle(keyword):
    jobs = []
    query = keyword.replace(" ", "%20")
    url = f"https://uae.dubizzle.com/jobs/?search={query}"

    response = http_get(url)
    if response is None or response.status_code != 200:
        code = response.status_code if response is not None else "no response"
        print(f"  [Dubizzle] Failed '{keyword}' — {code}")
        return jobs

    soup = BeautifulSoup(response.text, "html.parser")
    for listing in soup.find_all("article")[:25]:
        try:
            title_tag = listing.find("h2") or listing.find("h3")
            company_tag = listing.find("span", {"class": lambda c: c and "company" in str(c).lower()})
            location_tag = listing.find("span", {"class": lambda c: c and "location" in str(c).lower()})
            link_tag = listing.find("a", href=True)
            if not title_tag or not link_tag:
                continue
            href = link_tag["href"]
            jobs.append({
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": location_tag.get_text(strip=True) if location_tag else "",
                "url": "https://uae.dubizzle.com" + href if href.startswith("/") else href,
                "source": "Dubizzle",
            })
        except Exception:
            continue
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
            return False
        return True
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False


def format_job(job):
    badges = ""
    if job.get("emirati"):
        badges += " 🇦🇪"
    if job.get("al_ain"):
        badges += " ⭐"
    lines = [
        f"💼 <b>{html.escape(job['title'])}</b>{badges}",
        f"• 🏢 {html.escape(job['company'])}",
        f"• 📍 {html.escape(job['location'])}",
    ]
    if job.get("salary"):
        lines.append(f"• 💰 {html.escape(job['salary'])}")
    lines.append(f"• 🌐 {html.escape(job['source'])}")
    lines.append(f"• 🔗 <a href=\"{html.escape(job['url'], quote=True)}\">Apply Now</a>")
    return "\n".join(lines) + "\n\n"


def send_jobs_in_chunks(jobs, total_new):
    """Returns True only if every message was delivered."""
    date_str = datetime.now().strftime("%d %b %Y")
    header = (
        f"🚀 <b>Job Alert — {date_str}</b>\n"
        f"Found <b>{total_new} new jobs</b> matching your profile\n"
        + (f"Showing the top <b>{len(jobs)}</b>, best matches first\n" if len(jobs) < total_new else "")
        + f"🇦🇪 = Emirati-targeted   ⭐ = Al Ain\n"
        f"{'─' * 30}\n\n"
    )

    ok = True
    current_message = header

    for job in jobs:
        job_text = format_job(job)

        if len(current_message) + len(job_text) > TELEGRAM_MAX_CHARS:
            ok = send_telegram_message(current_message) and ok
            time.sleep(TELEGRAM_SEND_DELAY_SEC)
            current_message = (
                "🚀 <b>Job Alert (continued)</b>\n"
                f"{'─' * 30}\n\n"
            )

        current_message += job_text

    current_message += "\n💪 Good luck Abdul Rahman!"
    ok = send_telegram_message(current_message) and ok
    return ok


def send_no_jobs_message():
    date_str = datetime.now().strftime("%d %b %Y")
    send_telegram_message(
        f"📭 <b>Job Alert — {date_str}</b>\n\n"
        "No new jobs found today matching your profile.\n\n"
        "Keep your applications going — new listings appear daily!"
    )


# ============================================================
# MAIN
# ============================================================

# Each job board gets its own worker thread (so they run side by side instead of
# one after another). Inside a worker the requests are still sequential and polite.

def _worker_linkedin():
    out = []
    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            out.append(scrape_linkedin(keyword, location))
            time.sleep(3)
    return out


def _worker_indeed():
    out = []
    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            out.append(scrape_indeed(keyword, location))
            time.sleep(1)
    return out


def _worker_bayt():
    out = []
    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            out.append(scrape_bayt(keyword, location))
            time.sleep(1)
    return out


def _worker_gulftalent():
    out = []
    for keyword in SEARCH_KEYWORDS:
        out.append(scrape_gulftalent(keyword))
        time.sleep(1)
    return out


def _worker_dubizzle():
    out = []
    for keyword in SEARCH_KEYWORDS:
        out.append(scrape_dubizzle(keyword))
        time.sleep(1)
    return out


SOURCE_WORKERS = {
    "linkedin": ("LinkedIn", _worker_linkedin),
    "indeed": ("Indeed", _worker_indeed),
    "bayt": ("Bayt", _worker_bayt),
    "gulftalent": ("GulfTalent", _worker_gulftalent),
    "dubizzle": ("Dubizzle", _worker_dubizzle),
}


def main():
    started = time.time()
    print(f"\n{'='*50}")
    print(f"Job Scraper Started — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*50}\n")

    seen_jobs = load_seen_jobs()
    candidates = {}   # job id -> job

    active = [(label, fn) for key, (label, fn) in SOURCE_WORKERS.items() if ENABLED_SOURCES.get(key)]
    print(f"Searching {len(SEARCH_KEYWORDS)} keywords x {len(LOCATIONS)} locations on: "
          f"{', '.join(label for label, _ in active)}\n")

    with ThreadPoolExecutor(max_workers=max(1, len(active))) as pool:
        futures = [(label, pool.submit(fn)) for label, fn in active]

        for label, future in futures:
            try:
                batches = future.result()
            except Exception as e:
                print(f"  [{label}] crashed: {e}")
                continue
            scraped = relevant = 0
            for batch in batches:
                for raw in batch:
                    scraped += 1
                    job = evaluate_job(raw)
                    if not job or job["id"] in seen_jobs:
                        continue
                    relevant += 1
                    existing = candidates.get(job["id"])
                    if existing is None or job["score"] > existing["score"]:
                        candidates[job["id"]] = job
            print(f"  [{label}] {scraped} scraped, {relevant} new & relevant")

    all_jobs = sorted(candidates.values(), key=lambda j: j["score"], reverse=True)
    print(f"\nTotal new jobs found: {len(all_jobs)}")

    if all_jobs:
        to_send = all_jobs[:MAX_JOBS_PER_RUN]
        if send_jobs_in_chunks(to_send, len(all_jobs)):
            print(f"[Telegram] Notification sent ({len(to_send)} of {len(all_jobs)} jobs)!")
            # Only mark what was actually sent — the rest can show up in the next run
            for job in to_send:
                seen_jobs.add(job["id"])
            save_seen_jobs(seen_jobs)
        else:
            print("[Telegram] Sending failed — jobs NOT marked as seen, will retry next run.")
    else:
        send_no_jobs_message()
        print("[Telegram] No new jobs notification sent.")

    print(f"\nDone in {(time.time() - started) / 60:.1f} min!")


if __name__ == "__main__":
    main()