# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# users: { id (bigint, PK), phone (text), social (text), email (text, nullable), cookies (jsonb, nullable) }
# trackers: { id (uuid, default), user_id (bigint), service_id (text), branch_id (text),
#             last_best_date (text, nullable), enabled (bool), created_at (timestamptz) }

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    res = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    if res.data:
        return res.data[0]
    return None

def upsert_user(user_id: int, phone: str, social: str, email: Optional[str] = None, cookies: Optional[dict] = None) -> Dict[str, Any]:
    record = {"id": user_id, "tg_user_id": user_id, "phone": phone, "social": social}
    if email is not None:
        record["email"] = email
    if cookies is not None:
        record["cookies"] = cookies
    supabase.table("users").upsert(record).execute()
    return record

def update_user(user_id: int, fields: Dict[str, Any]) -> None:
    supabase.table("users").update(fields).eq("id", user_id).execute()

def save_cookies(user_id: int, cookies: dict) -> None:
    supabase.table("users").update({"cookies": cookies}).eq("id", user_id).execute()

def get_trackers_for_user(user_id: int) -> List[Dict[str, Any]]:
    res = supabase.table("trackers").select("*").eq("user_id", user_id).eq("enabled", True).execute()
    return res.data or []

def upsert_tracker(user_id: int, service_id: str, branch_id: str, last_best_date: Optional[str] = None, enabled: bool = True) -> None:
    supabase.table("trackers").upsert({
        "user_id": user_id,
        "service_id": service_id,
        "branch_id": branch_id,
        "last_best_date": last_best_date,
        "enabled": enabled
    }, on_conflict="user_id,service_id,branch_id").execute()

def update_tracker_last_date(user_id: int, service_id: str, branch_id: str, last_best_date: Optional[str]) -> None:
    supabase.table("trackers").update({"last_best_date": last_best_date}).eq("user_id", user_id)\
        .eq("service_id", service_id).eq("branch_id", branch_id).execute()

def disable_tracker(user_id: int, service_id: str, branch_id: str) -> None:
    supabase.table("trackers").update({"enabled": False}).eq("user_id", user_id)\
        .eq("service_id", service_id).eq("branch_id", branch_id).execute()
