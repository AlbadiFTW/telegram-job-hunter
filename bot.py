"""
bot.py
Interactive Telegram bot for tracking job applications.
Run this locally: python bot.py

Commands:
  /applied <company> <role>  — Log a new application
  /interview <company>       — Mark company as reached interview stage
  /rejected <company>        — Mark company as rejected you
  /offer <company>           — Mark company as gave you an offer 🎉
  /stats                     — Show all-time stats
  /list                      — Show this week's applications
  /help                      — Show all commands
"""

import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

from config import (
    TELEGRAM_BOT_TOKEN as _CONFIG_TOKEN,
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", _CONFIG_TOKEN)
APPLICATIONS_FILE = "applications.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# ============================================================
# DATA HELPERS
# ============================================================

def load_applications():
    if os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_applications(apps):
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2)


def find_application(apps, company):
    """Find most recent application matching company name (case insensitive)."""
    company_lower = company.lower()
    matches = [a for a in apps if company_lower in a["company"].lower()]
    return matches[-1] if matches else None


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

    apps = load_applications()
    new_app = {
        "company": company,
        "role": role,
        "status": "applied",
        "date": datetime.now().isoformat(),
    }
    apps.append(new_app)
    save_applications(apps)

    total = len(apps)
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
    apps = load_applications()
    app = find_application(apps, company)

    if not app:
        await update.message.reply_text(
            f"❌ No application found for <b>{company}</b>.\n"
            f"Log it first with /applied",
            parse_mode="HTML"
        )
        return

    app["status"] = "interview"
    app["interview_date"] = datetime.now().isoformat()
    save_applications(apps)

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
    apps = load_applications()
    app = find_application(apps, company)

    if not app:
        await update.message.reply_text(
            f"❌ No application found for <b>{company}</b>.",
            parse_mode="HTML"
        )
        return

    app["status"] = "rejected"
    save_applications(apps)

    total = len(apps)
    rejections = len([a for a in apps if a.get("status") == "rejected"])

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
    apps = load_applications()
    app = find_application(apps, company)

    if not app:
        await update.message.reply_text(
            f"❌ No application found for <b>{company}</b>.",
            parse_mode="HTML"
        )
        return

    app["status"] = "offer"
    save_applications(apps)

    await update.message.reply_text(
        f"🎉 <b>OFFER RECEIVED!</b>\n\n"
        f"🏢 {app['company']} — {app['role']}\n\n"
        f"Congratulations Abdul Rahman! All that hard work paid off! 🚀",
        parse_mode="HTML"
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apps = load_applications()

    if not apps:
        await update.message.reply_text(
            "📊 No applications logged yet.\n"
            "Start with: /applied &lt;company&gt; &lt;role&gt;",
            parse_mode="HTML"
        )
        return

    total = len(apps)
    interviews = len([a for a in apps if a.get("status") == "interview"])
    rejected = len([a for a in apps if a.get("status") == "rejected"])
    offers = len([a for a in apps if a.get("status") == "offer"])
    pending = len([a for a in apps if a.get("status") == "applied"])
    interview_rate = round((interviews / total * 100), 1) if total > 0 else 0

    # This week
    week_ago = datetime.now() - timedelta(days=7)
    this_week = len([
        a for a in apps
        if datetime.fromisoformat(a["date"]) > week_ago
    ])

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
    apps = load_applications()

    if not apps:
        await update.message.reply_text(
            "📋 No applications logged yet.\n"
            "Start with: /applied &lt;company&gt; &lt;role&gt;",
            parse_mode="HTML"
        )
        return

    week_ago = datetime.now() - timedelta(days=7)
    this_week = [
        a for a in apps
        if datetime.fromisoformat(a["date"]) > week_ago
    ]

    if not this_week:
        await update.message.reply_text("📋 No applications this week yet.")
        return

    status_emoji = {
        "applied": "📤",
        "interview": "🎯",
        "rejected": "❌",
        "offer": "🎉"
    }

    lines = ""
    for app in this_week:
        emoji = status_emoji.get(app.get("status"), "📤")
        date_str = datetime.fromisoformat(app["date"]).strftime("%d %b")
        lines += f"{emoji} <b>{app['company']}</b> — {app['role']} ({date_str})\n"

    await update.message.reply_text(
        f"📋 <b>This Week's Applications ({len(this_week)})</b>\n"
        f"{'─' * 25}\n\n"
        f"{lines}",
        parse_mode="HTML"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print("Starting JobHunter Bot...")
    print("Press Ctrl+C to stop.\n")

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