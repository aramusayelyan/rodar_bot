import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")  # e.g. https://your-service.onrender.com
PORT = int(os.getenv("PORT", "10000"))

# Supabase REST (optional but recommended)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")  # e.g. https://xxxx.supabase.co
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # service_role key recommended (kept server-side only)
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "users")  # default table name

# RoadPolice site
RP_BASE = "https://roadpolice.am"
RP_LANG = "hy"  # Armenian

# Tracking (nearest-day refresh)
TRACK_INTERVAL_MINUTES = int(os.getenv("TRACK_INTERVAL_MINUTES", "120"))  # every 2h by default
LOOKAHEAD_DAYS = int(os.getenv("LOOKAHEAD_DAYS", "30"))  # search window for listing free days

# Validation
PHONE_HINT = "Մուտքագրեք ձևաչափով՝ +374XXXXXXXX կամ 0XXXXXXXX"
EMAIL_HINT = "Մուտքագրեք Ձեր էլ․ փոստը (օր․: name@example.com)"
DATE_FORMAT_HINT = "Օրինակ՝ 12-08-2025 (ՕՕ-ԱԱ-ՏՏՏՏ)"
HOUR_FORMAT_HINT = "Օրինակ՝ 09:00"
