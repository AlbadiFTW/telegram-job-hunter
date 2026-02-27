"""
weekly_summary.py
Sends a weekly job application summary every Sunday at 9AM UAE time.
Runs via GitHub Actions on a schedule.
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

from config import (
    TELEGRAM_BOT_TOKEN as _CONFIG_TOKEN,
    TELEGRAM_CHAT_ID as _CONFIG_CHAT_ID,
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", _CONFIG_TOKEN)
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", _CONFIG_CHAT_ID)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gmxjjqpoehbsjtqgbdot.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def get_applications():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/applications?order=date.desc",
        headers=SUPABASE_HEADERS,
        timeout=10
    )
    data = response.json()
    if not isinstance(data, list):
        print(f"[Supabase] Unexpected response: {data}")
        return []
    return data


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
        print("[Telegram] Weekly summary sent!")


def main():
    print(f"Weekly Summary — {datetime.now().strftime('%d %b %Y %H:%M')}")

    apps = get_applications()

    if not apps:
        send_telegram_message(
            "📊 <b>Weekly Summary</b>\n"
            f"Week ending {datetime.now().strftime('%d %b %Y')}\n"
            f"{'─' * 30}\n\n"
            "No applications logged yet this week.\n\n"
            "Start with:\n<code>/applied &lt;company&gt; &lt;role&gt;</code>"
        )
        return

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    this_week = [a for a in apps if datetime.fromisoformat(a["date"]) > week_ago]

    total = len(apps)
    this_week_count = len(this_week)
    interviews = len([a for a in apps if a.get("status") == "interview"])
    rejected = len([a for a in apps if a.get("status") == "rejected"])
    offers = len([a for a in apps if a.get("status") == "offer"])
    pending = len([a for a in apps if a.get("status") == "applied"])
    interview_rate = round((interviews / total * 100), 1) if total > 0 else 0

    week_list = ""
    status_emoji = {"applied": "📤", "interview": "🎯", "rejected": "❌", "offer": "🎉"}
    for app in this_week[:10]:
        emoji = status_emoji.get(app.get("status"), "📤")
        week_list += f"{emoji} {app['company']} — {app['role']}\n"

    message = (
        f"📊 <b>Weekly Job Hunt Summary</b>\n"
        f"Week ending {datetime.now().strftime('%d %b %Y')}\n"
        f"{'─' * 30}\n\n"
        f"<b>Totals</b>\n"
        f"• This week: {this_week_count} applications\n"
        f"• All time: {total} applications\n\n"
        f"<b>Outcomes</b>\n"
        f"• 🎯 Interviews: {interviews}\n"
        f"• ❌ Rejections: {rejected}\n"
        f"• 🎉 Offers: {offers}\n"
        f"• ⏳ Pending: {pending}\n"
        f"• 📈 Interview rate: {interview_rate}%\n\n"
    )

    if week_list:
        message += f"<b>This week's applications</b>\n{week_list}\n"

    if this_week_count < 10:
        message += f"💡 <i>Target: 10 applications/day. You sent {this_week_count} this week — keep pushing!</i>\n"
    else:
        message += "🔥 <i>Great week — keep the momentum going!</i>\n"

    message += "\n💪 Good luck Abdul Rahman!"

    send_telegram_message(message)
    print("Done!")


if __name__ == "__main__":
    main()