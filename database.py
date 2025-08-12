import json
import time
from typing import Optional, Dict, Any
import httpx
import logging
import config

logger = logging.getLogger(__name__)

# If Supabase variables are missing, fall back to in-memory store
_USE_SB = bool(config.SUPABASE_URL and config.SUPABASE_KEY)

# In-memory fallback stores (for dev)
_MEM_USERS: Dict[str, Dict[str, Any]] = {}
_MEM_TRACKERS: Dict[str, Dict[str, Any]] = {}

def _sb_headers():
    return {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def get_user(tg_user_id: int) -> Optional[Dict[str, Any]]:
    if not _USE_SB:
        return _MEM_USERS.get(str(tg_user_id))
    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}"
    params = {"select": "*", "tg_user_id": f"eq.{tg_user_id}", "limit": "1"}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(url, params=params, headers=_sb_headers())
        r.raise_for_status()
        data = r.json()
        return data[0] if data else None

def upsert_user_fields(tg_user_id: int, **fields):
    record = {"tg_user_id": str(tg_user_id)}
    record.update(fields)
    if not _USE_SB:
        user = _MEM_USERS.get(str(tg_user_id), {})
        user.update(record)
        _MEM_USERS[str(tg_user_id)] = user
        return

    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}"
    with httpx.Client(timeout=15.0) as client:
        r = client.post(url, params={"on_conflict": "tg_user_id"}, headers=_sb_headers(), json=record)
        if r.status_code not in (200, 201):
            logger.error("Supabase upsert failed: %s %s", r.status_code, r.text)
        else:
            logger.info("Supabase upsert OK")

def save_cookies(tg_user_id: int, cookies: Dict[str, str]):
    upsert_user_fields(tg_user_id, cookies=json.dumps(cookies), updated_at=int(time.time()))

def load_cookies(tg_user_id: int) -> Dict[str, str]:
    u = get_user(tg_user_id)
    if u and u.get("cookies"):
        try:
            return json.loads(u["cookies"])
        except Exception:
            return {}
    return {}

def set_verified(tg_user_id: int, verified: bool):
    upsert_user_fields(tg_user_id, verified=verified, updated_at=int(time.time()))

def get_verified(tg_user_id: int) -> bool:
    u = get_user(tg_user_id)
    return bool(u and u.get("verified"))

# Trackers (in-memory to keep it simple/free)
def set_tracker(chat_id: int, branch_id: str, service_id: str, last_day: Optional[str]):
    _MEM_TRACKERS[str(chat_id)] = {
        "branch_id": branch_id, "service_id": service_id, "last_day": last_day
    }

def get_tracker(chat_id: int) -> Optional[Dict[str, Any]]:
    return _MEM_TRACKERS.get(str(chat_id))

def clear_tracker(chat_id: int):
    _MEM_TRACKERS.pop(str(chat_id), None)
