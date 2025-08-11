# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

SUPABASE_URL = (os.getenv("SUPABASE_URL", "") or os.getenv("SUPABASE_PROJECT_URL", "")).strip()

# Accept multiple common env var names to avoid mismatch on Render
_SUPA_KEYS = [
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SERVICE",
    "SUPABASE_ANON_KEY",
]
SUPABASE_KEY = ""
for k in _SUPA_KEYS:
    v = os.getenv(k)
    if v and v.strip():
        SUPABASE_KEY = v.strip()
        break

TRACK_INTERVAL_MINUTES = int(os.getenv("TRACK_INTERVAL_MINUTES", "120"))

# Hard fail early with a clear message if something is missing
missing = []
if not BOT_TOKEN:
    missing.append("BOT_TOKEN")
if not SUPABASE_URL:
    missing.append("SUPABASE_URL")
if not SUPABASE_KEY:
    missing.append("SUPABASE_KEY (or SUPABASE_SERVICE_KEY / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY)")
if missing:
    raise SystemExit("Missing required environment variables: " + ", ".join(missing))
