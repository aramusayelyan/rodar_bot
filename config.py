import os

# ⚠️ Թոքենը պահիր ENV-ում Render-ում՝ TELEGRAM_TOKEN անունով:
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN env var is missing!")
