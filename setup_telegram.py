"""
Run this script ONCE after creating your Telegram bot to get your Chat ID.

Steps:
1. Message @BotFather on Telegram → /newbot → follow instructions
2. Copy the bot token BotFather gives you
3. Message your new bot (send it any message like "hello")
4. Replace YOUR_BOT_TOKEN below and run this script
5. Copy the chat_id from the output
6. Add both to config.py and GitHub Secrets
"""

import requests

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your token from @BotFather

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if data["ok"] and data["result"]:
    chat_id = data["result"][0]["message"]["chat"]["id"]
    print(f"\n✅ Your Chat ID is: {chat_id}")
    print(f"\nAdd these to config.py:")
    print(f'TELEGRAM_BOT_TOKEN = "{BOT_TOKEN}"')
    print(f'TELEGRAM_CHAT_ID = "{chat_id}"')
else:
    print("\n❌ No messages found.")
    print("Make sure you sent your bot a message first, then run this again.")
    print(f"\nRaw response: {data}")
