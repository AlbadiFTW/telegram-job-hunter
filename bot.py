"""
bot.py
Interactive Telegram bot for tracking job applications.
Deploy to Render as a background worker — runs 24/7.

Commands:
  /applied <company> <role>  — Log a new application
  /interview <company>       — Mark as interview stage
  /rejected <company>        — Mark as rejected
  /offer <company>           — Mark as offer received
  /stats                     — Show all-time stats
  /list                      — Show this week's applications
  /help                      — Show all commands
"""

import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

from config import TELEGRAM_BOT_TOKEN as _CONFIG_TOKEN
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", _CONFIG_TOKEN)

# --- Supabase Config ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gmxjjqpoehbsjtqgbdot.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# ============================================================
# SUPABASE HELPERS
# ============================================================

def db_insert(data: dict):
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/applications",
        headers=SUPABASE_HEADERS,
        json=data,
        timeout=10
    )
    return response.json()


def db_get_all():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/applications?order=date.desc",
        headers=SUPABASE_HEADERS,
        timeout=10
    )
    return response.json()


def db_update(app_id: int, data: dict):
    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/applications?id=eq.{app_id}",
        headers=SUPABASE_HEADERS,
        json=data,
        timeout=10
    )
    return response.json()


def find_application(company: str):
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/applications?company=ilike.*{company}*&order=date.desc&limit=1",
        headers=SUPABASE_HEADERS,
        timeout=10
    )
    results = response.json()
    return results[0] if results else None


# ============================================================
# COMMAND HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>JobHunter Bot</b>\n\n"
        "I help you track your job applications. Here's what I can do:\n\n"
        "/applied &lt;company&gt; &lt;role&gt; — Log a new application\n"
        "/interview &lt;company&gt; — Mark as interview stage\n"
        "/rejected &lt;company&gt; — Mark as rejected\n"
        "/offer &lt;company&gt; — Mark as offer received 🎉\n"
        "/stats — View all-time stats\n"
        "/list — View this week's applications\n"
        "/help — Show this message",
        parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_applied(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Usage: /applied &lt;company&gt; &lt;role&gt;\n"
            "Example: /applied Noon 'Full Stack Engineer'",
            parse_mode="HTML"
        )
        return

    company = args[0]
    role = " ".join(args[1:])

    db_insert({"company": company, "role": role, "status": "applied"})
    all_apps = db_get_all()
    total = len(all_apps)

    await update.message.reply_text(
        f"✅ <b>Application logged!</b>\n\n"
        f"🏢 {company}\n"
        f"💼 {role}\n"
        f"📅 {datetime.now().strftime('%d %b %Y')}\n\n"
        f"Total applications: <b>{total}</b>",
        parse_mode="HTML"
    )


async def cmd_interview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /interview &lt;company&gt;", parse_mode="HTML")
        return

    company = " ".join(context.args)
    app = find_application(company)

    if not app:
        await update.message.reply_text(
            f"❌ No application found for <b>{company}</b>.\nLog it first with /applied",
            parse_mode="HTML"
        )
        return

    db_update(app["id"], {"status": "interview", "interview_date": datetime.now(timezone.utc).isoformat()})

    await update.message.reply_text(
        f"🎯 <b>Interview stage!</b>\n\n"
        f"🏢 {app['company']} — {app['role']}\n\n"
        f"Prepare well. You've got this 💪",
        parse_mode="HTML"
    )


async def cmd_rejected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /rejected &lt;company&gt;", parse_mode="HTML")
        return

    company = " ".join(context.args)
    app = find_application(company)

    if not app:
        await update.message.reply_text(f"❌ No application found for <b>{company}</b>.", parse_mode="HTML")
        return

    db_update(app["id"], {"status": "rejected"})
    all_apps = db_get_all()
    total = len(all_apps)
    rejections = len([a for a in all_apps if a.get("status") == "rejected"])

    await update.message.reply_text(
        f"❌ <b>Rejection logged</b>\n\n"
        f"🏢 {app['company']} — {app['role']}\n\n"
        f"Rejections: {rejections}/{total}\n"
        f"Every rejection is one step closer. Keep going 💪",
        parse_mode="HTML"
    )


async def cmd_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /offer &lt;company&gt;", parse_mode="HTML")
        return

    company = " ".join(context.args)
    app = find_application(company)

    if not app:
        await update.message.reply_text(f"❌ No application found for <b>{company}</b>.", parse_mode="HTML")
        return

    db_update(app["id"], {"status": "offer"})

    await update.message.reply_text(
        f"🎉 <b>OFFER RECEIVED!</b>\n\n"
        f"🏢 {app['company']} — {app['role']}\n\n"
        f"Congratulations Abdul Rahman! All that hard work paid off! 🚀",
        parse_mode="HTML"
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_apps = db_get_all()

    if not all_apps:
        await update.message.reply_text(
            "📊 No applications logged yet.\nStart with: /applied &lt;company&gt; &lt;role&gt;",
            parse_mode="HTML"
        )
        return

    total = len(all_apps)
    interviews = len([a for a in all_apps if a.get("status") == "interview"])
    rejected = len([a for a in all_apps if a.get("status") == "rejected"])
    offers = len([a for a in all_apps if a.get("status") == "offer"])
    pending = len([a for a in all_apps if a.get("status") == "applied"])
    interview_rate = round((interviews / total * 100), 1) if total > 0 else 0

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    this_week = len([a for a in all_apps if datetime.fromisoformat(a["date"]) > week_ago])

    await update.message.reply_text(
        f"📊 <b>Application Stats</b>\n"
        f"{'─' * 25}\n\n"
        f"📤 Total applied: <b>{total}</b>\n"
        f"📅 This week: <b>{this_week}</b>\n\n"
        f"🎯 Interviews: <b>{interviews}</b>\n"
        f"❌ Rejections: <b>{rejected}</b>\n"
        f"🎉 Offers: <b>{offers}</b>\n"
        f"⏳ Pending: <b>{pending}</b>\n\n"
        f"📈 Interview rate: <b>{interview_rate}%</b>",
        parse_mode="HTML"
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_apps = db_get_all()

    if not all_apps:
        await update.message.reply_text(
            "📋 No applications logged yet.\nStart with: /applied &lt;company&gt; &lt;role&gt;",
            parse_mode="HTML"
        )
        return

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    this_week = [a for a in all_apps if datetime.fromisoformat(a["date"]) > week_ago]

    if not this_week:
        await update.message.reply_text("📋 No applications this week yet.")
        return

    status_emoji = {"applied": "📤", "interview": "🎯", "rejected": "❌", "offer": "🎉"}
    lines = ""
    for app in this_week[:15]:
        emoji = status_emoji.get(app.get("status"), "📤")
        date_str = datetime.fromisoformat(app["date"]).strftime("%d %b")
        lines += f"{emoji} <b>{app['company']}</b> — {app['role']} ({date_str})\n"

    await update.message.reply_text(
        f"📋 <b>This Week's Applications ({len(this_week)})</b>\n"
        f"{'─' * 25}\n\n{lines}",
        parse_mode="HTML"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    print("Starting JobHunter Bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("applied", cmd_applied))
    app.add_handler(CommandHandler("interview", cmd_interview))
    app.add_handler(CommandHandler("rejected", cmd_rejected))
    app.add_handler(CommandHandler("offer", cmd_offer))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("list", cmd_list))
    print("Bot is running. Send /help to your bot on Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()