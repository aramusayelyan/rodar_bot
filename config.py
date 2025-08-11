import os

# Render-ում դնում ես Environment → Variables
# Key: BOT_TOKEN  |  Value: <քո թոքենը>
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN environment variable.")

# project-ի այլ մասերում հարմար լինելու համար
TELEGRAM_TOKEN = BOT_TOKEN
