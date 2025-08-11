# -*- coding: utf-8 -*-
import os
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY", "").strip()
    or os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase env vars missing: SUPABASE_URL and SUPABASE_KEY (or SERVICE/ANON).")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    res = supabase.table("users").select("*").eq("tg_user_id", user_id).limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def upsert_user(user_id: int, phone: str, social: str, cookies: Optional[Dict[str, str]] = None) -> None:
    record = {
        "tg_user_id": user_id,
        "phone": phone,
        "social": social,
        "cookies": cookies or {},
    }
    supabase.table("users").upsert(record, on_conflict="tg_user_id").execute()


def save_cookies(user_id: int, cookies: Dict[str, str]) -> None:
    supabase.table("users").update({"cookies": cookies}).eq("tg_user_id", user_id).execute()


def upsert_tracker(user_id: int, service_id: str, branch_id: str, last_best_date: Optional[str] = None) -> None:
    record = {
        "tg_user_id": user_id,
        "service_id": service_id,
        "branch_id": branch_id,
        "last_best_date": last_best_date,
    }
    supabase.table("trackers").upsert(record, on_conflict="tg_user_id,service_id,branch_id").execute()


def get_all_trackers() -> List[Dict[str, Any]]:
    res = supabase.table("trackers").select("*").execute()
    return res.data or []


def update_tracker_last_date(user_id: int, service_id: str, branch_id: str, day: str) -> None:
    supabase.table("trackers").update({"last_best_date": day}).match(
        {"tg_user_id": user_id, "service_id": service_id, "branch_id": branch_id}
    ).execute()
