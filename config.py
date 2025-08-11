# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()  # use service role key or anon as you prefer

# Job (nearest-day tracking) interval in minutes
TRACK_INTERVAL_MINUTES = int(os.getenv("TRACK_INTERVAL_MINUTES", "120"))
