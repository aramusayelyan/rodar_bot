import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Webhook
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "10000"))  # Render will inject PORT

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# Roadpolice base settings
RP_BASE = "https://roadpolice.am"
RP_LANG = "hy"  # Armenian UI

# App behavior
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36"
)
REQUEST_TIMEOUT = 25  # seconds
TRACKER_INTERVAL_MIN = 120  # every 2 hours
