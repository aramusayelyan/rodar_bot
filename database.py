# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
import config

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# ---------- Users ----------
def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    res = supabase.table("users").select("*").eq("tg_user_id", user_id).limit(1).execute()
    if res.data:
        return res.data[0]
    return None

def upsert_user(user_id: int, phone: str, social: str, cookies: Dict[str, str]):
    record = {"tg_user_id": user_id, "phone": phone, "social": social, "cookies": cookies}
    try:
        supabase.table("users").upsert(record, on_conflict="tg_user_id").execute()
    except Exception:
        supabase.table("users").upsert(record).execute()

def save_cookies(user_id: int, cookies: Dict[str, str]):
    supabase.table("users").update({"cookies": cookies}).eq("tg_user_id", user_id).execute()

# ---------- Trackers ----------
def upsert_tracker(user_id: int, service_id: str, branch_id: str, last_best_date: Optional[str] = None):
    record = {
        "tg_user_id": user_id,
        "service_id": service_id,
        "branch_id": branch_id,
        "last_best_date": last_best_date or None,
        "enabled": True,
    }
    try:
        supabase.table("trackers").upsert(record, on_conflict="tg_user_id,service_id,branch_id").execute()
    except Exception:
        supabase.table("trackers").upsert(record).execute()

def get_all_trackers() -> List[Dict[str, Any]]:
    res = supabase.table("trackers").select("*").eq("enabled", True).execute()
    return res.data or []

def update_tracker_last_date(user_id: int, service_id: str, branch_id: str, new_date: str):
    supabase.table("trackers").update({"last_best_date": new_date}).eq("tg_user_id", user_id).eq("service_id", service_id).eq("branch_id", branch_id).execute()
