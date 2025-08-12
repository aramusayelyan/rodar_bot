import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
PORT = int(os.getenv("PORT", "10000"))

# Supabase (optional)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "users")

# RoadPolice site
RP_BASE = "https://roadpolice.am"
RP_LANG = "hy"  # Armenian

# Search behavior
TRACK_INTERVAL_MINUTES = int(os.getenv("TRACK_INTERVAL_MINUTES", "120"))  # refresh every 2h
LOOKAHEAD_DAYS = int(os.getenv("LOOKAHEAD_DAYS", "30"))

# Hints
PHONE_HINT = "Մուտքագրեք ձևաչափով՝ +374XXXXXXXX կամ 0XXXXXXXX"
EMAIL_HINT = "Մուտքագրեք Ձեր էլ․ փոստը (օր․: name@example.com)"
DATE_FORMAT_HINT = "Օրինակ՝ 12-08-2025 (ՕՕ-ԱԱ-ՏՏՏՏ)"
HOUR_FORMAT_HINT = "Օրինակ՝ 09:00"
