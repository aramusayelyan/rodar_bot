# -*- coding: utf-8 -*-
import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Webhook (Render)
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip()  # e.g. https://your-service.onrender.com
PORT = int(os.getenv("PORT", "10000"))

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# Tracker interval (minutes)
TRACK_INTERVAL_MINUTES = int(os.getenv("TRACK_INTERVAL_MINUTES", "120"))
