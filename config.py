import os

# Կարդում ենք միայն BOT_TOKEN միջավայրային փոփոխականը
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN environment variable.")

# Եթե կոդում օգտագործվում է TELEGRAM_TOKEN, թող նույն արժեքը ստանա
TELEGRAM_TOKEN = BOT_TOKEN
