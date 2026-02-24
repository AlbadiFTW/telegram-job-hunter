"""
daily_question.py
Sends one technical and one behavioural interview question every morning.
Runs via GitHub Actions on a schedule.
"""

import os
import json
import random
import requests
from datetime import datetime
from dotenv import load_dotenv
from questions import TECHNICAL_QUESTIONS, BEHAVIOURAL_QUESTIONS

load_dotenv()

from config import (
    TELEGRAM_BOT_TOKEN as _CONFIG_TOKEN,
    TELEGRAM_CHAT_ID as _CONFIG_CHAT_ID,
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", _CONFIG_TOKEN)
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", _CONFIG_CHAT_ID)

SEEN_QUESTIONS_FILE = "seen_questions.json"


def load_seen_questions():
    if os.path.exists(SEEN_QUESTIONS_FILE):
        with open(SEEN_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"technical": [], "behavioural": []}


def save_seen_questions(seen):
    with open(SEEN_QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f)


def pick_question(questions, seen_list):
    """Pick a question not seen recently. Reset if all seen."""
    unseen = [q for q in questions if q not in seen_list]
    if not unseen:
        seen_list.clear()
        unseen = questions
    question = random.choice(unseen)
    seen_list.append(question)
    return question


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code != 200:
        print(f"[Telegram] Failed: {response.text}")
    else:
        print("[Telegram] Question sent!")


def main():
    print(f"Daily Question Sender — {datetime.now().strftime('%d %b %Y %H:%M')}")

    seen = load_seen_questions()

    tech_q = pick_question(TECHNICAL_QUESTIONS, seen["technical"])
    behav_q = pick_question(BEHAVIOURAL_QUESTIONS, seen["behavioural"])

    message = (
        f"🧠 <b>Daily Interview Prep — {datetime.now().strftime('%d %b %Y')}</b>\n"
        f"{'─' * 30}\n\n"
        f"💻 <b>Technical Question:</b>\n"
        f"{tech_q}\n\n"
        f"🗣 <b>Behavioural Question:</b>\n"
        f"{behav_q}\n\n"
        f"<i>Take 2 minutes to think through your answer before reading on today.</i>"
    )

    send_telegram_message(message)
    save_seen_questions(seen)
    print("Done!")


if __name__ == "__main__":
    main()