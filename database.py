import json
import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
import config

log = logging.getLogger(__name__)

supabase: Optional[Client] = None
if config.SUPABASE_URL and config.SUPABASE_KEY:
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
else:
    log.warning("Supabase creds missing; DB features will be disabled.")

def _safe_exec(fn, *args, **kwargs):
    if not supabase:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log.error("Supabase error: %s", e, exc_info=True)
        return None

def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
    res = _safe_exec(supabase.table("users").select("*").eq("id", tg_id).limit(1).execute)
    if not res or not res.data:
        return None
    row = res.data[0]
    # cookies may be dict already or string
    ck = row.get("cookies")
    if isinstance(ck, str):
        try:
            row["cookies"] = json.loads(ck)
        except Exception:
            row["cookies"] = None
    return row

def upsert_user(tg_id: int, phone: Optional[str] = None, social: Optional[str] = None, cookies: Optional[Dict[str, Any]] = None):
    record = {"id": tg_id}
    if phone is not None:
        record["phone"] = phone
    if social is not None:
        record["social"] = social
    if cookies is not None:
        record["cookies"] = cookies
    _safe_exec(supabase.table("users").upsert(record).execute)

def update_cookies(tg_id: int, cookies: Dict[str, Any]):
    upsert_user(tg_id, cookies=cookies)
