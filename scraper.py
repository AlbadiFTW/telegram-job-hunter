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
    SEARCH_KEYWORDS, SEARCH_QUERIES, LOCATIONS, ENABLED_SOURCES,
    ALLOWED_LOCATION_MARKERS, PRIORITY_LOCATIONS, PRIORITY_LOCATION_BONUS,
    PREFERRED_COMPANIES, PREFERRED_COMPANY_BONUS,
    EMIRATI_ONLY, EMIRATI_BONUS, EMIRATI_TITLE_KEYWORDS, EMIRATI_DESCRIPTION_KEYWORDS,
    SCORE_BOOST_KEYWORDS, SCORE_PENALTY_KEYWORDS, SECTOR_TITLE_KEYWORDS,
    REJECT_TITLE_KEYWORDS, REJECT_ANYWHERE_KEYWORDS, MAX_YEARS_EXPERIENCE,
    LINKEDIN_TIME_WINDOW, MAX_DETAIL_FETCHES_PER_RUN,
    SEEN_JOBS_FILE, MAX_JOBS_PER_RUN, SEND_EMPTY_NOTICE,
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
# (remembers jobs that were sent AND jobs that were opened and rejected,
#  so the slow description check never repeats for the same job)
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

_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
              "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_NUM_WORD_RE = re.compile(r"\b(" + "|".join(_NUM_WORDS) + r")\b(?=[^.\n]{0,12}\byears?\b)")
_YEARS_RE = re.compile(r"(\d{1,2})\s*(?:\+|\s*(?:-|–|—|to)\s*\d{1,2}\s*\+?)?\s*(?:years?|yrs?)\b")


def min_years_required(text):
    """Smallest 'N years' figure that sits next to the word 'experience', or None.
    Understands '3 years', '3+ years', '3-5 years', 'three (3) years', 'two to four years'."""
    text = re.sub(r"\(\s*\d+\s*\)", " ", text)                      # "three (3) years" -> "three  years"
    text = _NUM_WORD_RE.sub(lambda m: str(_NUM_WORDS[m.group(1)]), text)
    found = []
    for m in _YEARS_RE.finditer(text):
        window = text[max(0, m.start() - 60): m.end() + 60]
        if "experience" in window:
            found.append(int(m.group(1)))
    return min(found) if found else None


# ============================================================
# LOCATION FILTER — Abu Dhabi + Al Ain only
# ============================================================

def is_allowed_location(location):
    """True only for Abu Dhabi emirate (incl. Al Ain). An empty location is accepted
    because some boards don't show one; every real location must match."""
    loc = (location or "").lower().strip()
    if not loc:
        return True
    return has_any(loc, ALLOWED_LOCATION_MARKERS)


# ============================================================
# RELEVANCE SCORING
# ============================================================

def evaluate_job(raw, check_emirati=True):
    """Returns the job dict enriched with score/flags, or None if it should be skipped.
    check_emirati=False is used for the cheap first pass, before the description is read."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    description = raw.get("description") or ""
    company = raw.get("company") or "Unknown"
    location = raw.get("location") or ""

    title_l = title.lower()
    text = f"{title} {description}".lower()

    # --- hard rejects ---
    if not is_allowed_location(location):
        return None
    if has_any(title_l, REJECT_TITLE_KEYWORDS) or has_any(text, REJECT_ANYWHERE_KEYWORDS):
        return None

    years = min_years_required(text)
    if years is not None and years > MAX_YEARS_EXPERIENCE:
        return None

    # --- Emirati-targeted roles ---
    title_nat = _NON_EMIRATI_RE.sub(" ", title_l)
    desc_nat = _NON_EMIRATI_RE.sub(" ", description.lower())
    emirati = has_any(title_nat, EMIRATI_TITLE_KEYWORDS) or has_any(desc_nat, EMIRATI_DESCRIPTION_KEYWORDS)
    if check_emirati and EMIRATI_ONLY and not emirati:
        return None

    # --- base score: is it a sensible job for a fresh graduate? ---
    base = sum(b for kw, b in SCORE_BOOST_KEYWORDS if has(text, kw))
    base += sum(1 for kw in SECTOR_TITLE_KEYWORDS if has(title_l, kw))
    base += sum(p for kw, p in SCORE_PENALTY_KEYWORDS if has(title_l, kw))
    if base < MIN_SCORE:
        return None

    # --- ranking bonuses (added after the check above) ---
    score = base
    if emirati:
        score += EMIRATI_BONUS
    loc_l = f"{location} {title}".lower()
    al_ain = any(p in loc_l for p in PRIORITY_LOCATIONS)
    if al_ain:
        score += PRIORITY_LOCATION_BONUS
    if has_any(company.lower(), PREFERRED_COMPANIES):
        score += PREFERRED_COMPANY_BONUS

    return {
        "title": title,
        "company": company,
        "location": location or "Abu Dhabi",
        "url": raw.get("url", ""),
        "source": raw.get("source", ""),
        "score": score,
        "emirati": emirati,
        "al_ain": al_ain,
        "id": make_job_id(title, company),
    }


# ============================================================
# LINKEDIN SCRAPER
# ============================================================

def _linkedin_job_id(card, url):
    urn = card.get("data-entity-urn") or ""
    m = re.search(r"(\d{6,})\s*$", urn) or re.search(r"(\d{8,})(?:\?|$)", url or "")
    return m.group(1) if m else None


def scrape_linkedin(keyword, location, page=0):
    jobs = []
    query = keyword.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={query}&location={loc}&f_TPR={LINKEDIN_TIME_WINDOW}&start={page * 25}"
    )

    response = http_get(url)
    if response is None or response.status_code != 200:
        code = response.status_code if response is not None else "no response"
        print(f"  [LinkedIn] Failed '{keyword}' in {location.split(',')[0]} p{page + 1} — {code}")
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
            job_url = link_tag["href"].split("?")[0]
            jobs.append({
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": location_tag.get_text(strip=True) if location_tag else "",
                "url": job_url,
                "job_id": _linkedin_job_id(listing, job_url),
                "source": "LinkedIn",
            })
        except Exception:
            continue
    return jobs


def fetch_linkedin_description(job_id):
    """Full description + LinkedIn's criteria (seniority level etc.). None if it failed."""
    response = http_get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}")
    if response is None or response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    body = soup.find("div", {"class": "show-more-less-html__markup"})
    text = body.get_text(" ", strip=True) if body else ""
    criteria = " ".join(
        li.get_text(" ", strip=True)
        for li in soup.find_all("li", {"class": "description__job-criteria-item"})
    )
    combined = f"{criteria} {text}".strip()
    return combined or None


# ============================================================
# BAYT / GULFTALENT / DUBIZZLE (OFF by default — titles only, see config.py)
# ============================================================

def scrape_bayt(keyword, location):
    jobs = []
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
    city = re.sub(r"[^a-z0-9]+", "-", location.split(",")[0].lower()).strip("-")
    url = f"https://www.bayt.com/en/uae/jobs/{slug}-jobs-in-{city}/"

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
                "url": "https://www.gulftalent.com" + href if href.startswith("/") else href,
                "source": "GulfTalent",
            })
        except Exception:
            continue
    return jobs


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
        f"• 🌐 {html.escape(job['source'])}",
        f"• 🔗 <a href=\"{html.escape(job['url'], quote=True)}\">Apply Now</a>",
    ]
    return "\n".join(lines) + "\n\n"


def send_jobs_in_chunks(jobs, total_new):
    """Returns True only if every message was delivered."""
    date_str = datetime.now().strftime("%d %b %Y")
    scope = "Emiratization jobs" if EMIRATI_ONLY else "jobs"
    header = (
        f"🚀 <b>Job Alert — {date_str}</b>\n"
        f"Found <b>{total_new} new {scope}</b> in Abu Dhabi &amp; Al Ain\n"
        + (f"Showing the top <b>{len(jobs)}</b>, best matches first\n" if len(jobs) < total_new else "")
        + f"⭐ = Al Ain\n"
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
        "No new matching jobs found this time.\n\n"
        "Keep your applications going — new listings appear daily!"
    )


# ============================================================
# MAIN
# ============================================================

# Each enabled job board gets its own worker thread (so boards run side by side).

def _worker_linkedin():
    out = []
    for keyword, pages in SEARCH_QUERIES:
        for location in LOCATIONS:
            for page in range(pages):
                out.append(scrape_linkedin(keyword, location, page))
                time.sleep(3)
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
    "bayt": ("Bayt", _worker_bayt),
    "gulftalent": ("GulfTalent", _worker_gulftalent),
    "dubizzle": ("Dubizzle", _worker_dubizzle),
}


def read_descriptions(pending):
    """pending: list of (job_id, raw). Opens each LinkedIn job page (3 at a time, politely)."""
    def fetch(item):
        job_id, raw = item
        description = fetch_linkedin_description(raw["job_id"])
        time.sleep(1)
        return job_id, raw, description

    with ThreadPoolExecutor(max_workers=3) as pool:
        return list(pool.map(fetch, pending))


def main():
    started = time.time()
    print(f"\n{'='*50}")
    print(f"Job Scraper Started — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*50}\n")

    seen_jobs = load_seen_jobs()
    candidates = {}      # job id -> job that passed every filter
    needs_detail = {}    # job id -> (score, raw): looks promising, description not read yet
    rejected_ids = set() # opened, read, and rejected -> remembered so we never open them again

    active = [(label, fn) for key, (label, fn) in SOURCE_WORKERS.items() if ENABLED_SOURCES.get(key)]
    print(f"Sources: {', '.join(label for label, _ in active)} | "
          f"{len(SEARCH_QUERIES)} keywords x {len(LOCATIONS)} locations "
          f"(Abu Dhabi + Al Ain only)\n")

    # ---- 1. search ----
    with ThreadPoolExecutor(max_workers=max(1, len(active))) as pool:
        futures = [(label, pool.submit(fn)) for label, fn in active]

        for label, future in futures:
            try:
                batches = future.result()
            except Exception as e:
                print(f"  [{label}] crashed: {e}")
                continue
            scraped = promising = 0
            for batch in batches:
                for raw in batch:
                    scraped += 1
                    first_pass = evaluate_job(raw, check_emirati=False)   # location / title / seniority
                    if not first_pass or first_pass["id"] in seen_jobs or first_pass["id"] in candidates:
                        continue
                    if raw.get("source") == "LinkedIn" and raw.get("job_id"):
                        if first_pass["id"] not in needs_detail:
                            promising += 1
                        needs_detail[first_pass["id"]] = (first_pass["score"], raw)
                    else:
                        job = evaluate_job(raw)
                        if job:
                            promising += 1
                            candidates[job["id"]] = job
            print(f"  [{label}] {scraped} listings scraped, {promising} in Abu Dhabi/Al Ain and worth a closer look")

    # ---- 2. read the full description of the promising LinkedIn jobs ----
    pending = sorted(needs_detail.items(), key=lambda kv: kv[1][0], reverse=True)
    pending = [(job_id, raw) for job_id, (_, raw) in pending][:MAX_DETAIL_FETCHES_PER_RUN]
    skipped = len(needs_detail) - len(pending)
    print(f"\nReading {len(pending)} job descriptions"
          + (f" ({skipped} more next run)" if skipped else "") + "...")

    failed = 0
    for job_id, raw, description in read_descriptions(pending):
        if description is None:
            failed += 1          # not marked as seen -> retried next run
            continue
        raw["description"] = description
        job = evaluate_job(raw)
        if job:
            candidates[job["id"]] = job
        else:
            rejected_ids.add(job_id)
    if failed:
        print(f"  {failed} descriptions couldn't be loaded (will retry next run)")

    all_jobs = sorted(candidates.values(), key=lambda j: j["score"], reverse=True)
    print(f"\nMatching jobs (Emirati + 0-{MAX_YEARS_EXPERIENCE} yrs + Abu Dhabi/Al Ain): {len(all_jobs)}")

    # ---- 3. notify ----
    seen_jobs |= rejected_ids
    if all_jobs:
        to_send = all_jobs[:MAX_JOBS_PER_RUN]
        if send_jobs_in_chunks(to_send, len(all_jobs)):
            print(f"[Telegram] Notification sent ({len(to_send)} of {len(all_jobs)} jobs)!")
            seen_jobs |= {job["id"] for job in to_send}   # only what was actually sent
        else:
            print("[Telegram] Sending failed — jobs NOT marked as seen, will retry next run.")
    elif SEND_EMPTY_NOTICE:
        send_no_jobs_message()
        print("[Telegram] No new jobs notification sent.")
    else:
        print("Nothing new this run (no notification sent).")

    save_seen_jobs(seen_jobs)
    print(f"\nDone in {(time.time() - started) / 60:.1f} min!")


if __name__ == "__main__":
    main()