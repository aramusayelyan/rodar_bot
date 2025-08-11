# -*- coding: utf-8 -*-
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN")

# Render provides PORT; default to 10000
PORT = int(os.getenv("PORT", "10000"))

# Webhook base can come from explicit var or Render's external URL
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip() or os.getenv("RENDER_EXTERNAL_URL", "").strip()
if not WEBHOOK_BASE_URL:
    # We don't raise here; main.py will validate before starting webhook
    WEBHOOK_BASE_URL = ""

# Tracker interval (minutes)
TRACK_INTERVAL_MINUTES = int(os.getenv("TRACK_INTERVAL_MINUTES", "120"))
