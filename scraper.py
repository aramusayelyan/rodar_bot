# -*- coding: utf-8 -*-
import requests
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE = "https://roadpolice.am"
LANG = "hy"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"


def _attach_default_headers(s: requests.Session):
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE}/{LANG}/hqb",
            "Origin": BASE,
        }
    )


def cookies_to_dict(jar: requests.cookies.RequestsCookieJar) -> Dict[str, str]:
    return {c.name: c.value for c in jar}


def dict_to_cookiejar(cookies: Dict[str, str]) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for k, v in cookies.items():
        jar.set(k, v, domain="roadpolice.am", path="/")
    return jar


def _load_csrf(s: requests.Session) -> str:
    r = s.get(f"{BASE}/{LANG}/hqb", timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    csrf = meta["content"] if meta else ""
    if csrf:
        s.headers["X-CSRF-TOKEN"] = csrf
    return csrf


def new_session() -> Tuple[requests.Session, str]:
    s = requests.Session()
    _attach_default_headers(s)
    csrf = _load_csrf(s)
    return s, csrf


def ensure_session(cookies: Optional[Dict[str, str]] = None) -> Tuple[requests.Session, str]:
    if cookies:
        s = requests.Session()
        _attach_default_headers(s)
        s.cookies = dict_to_cookiejar(cookies)
        csrf = _load_csrf(s)
        return s, csrf
    return new_session()


# ---------- date helpers ----------
def _to_dd_mm_yyyy(dt: datetime) -> str:
    return dt.strftime("%d-%m-%Y")


def today_str() -> str:
    return _to_dd_mm_yyyy(datetime.now())


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _is_weekend(dt: datetime) -> bool:
    return dt.weekday() in (5, 6)  # Sat/Sun


# ---------- page scrape ----------
def get_branch_and_services(
    s: requests.Session,
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    r = s.get(f"{BASE}/{LANG}/hqb", timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    branches: List[Tuple[str, str]] = []
    services: List[Tuple[str, str]] = []

    bsel = soup.select("select[name='branchId'] option")
    ssel = soup.select("select[name='serviceId'] option")

    for o in bsel:
        val = o.get("value")
        if val:
            branches.append((o.text.strip(), val.strip()))
    for o in ssel:
        val = o.get("value")
        if val:
            services.append((o.text.strip(), val.strip()))
    return branches, services


# ---------- API calls ----------
def slots_for_month(
    sess: requests.Session, branch_id: str, service_id: str, date_dd_mm_yyyy: str
) -> List[str]:
    """Returns DISABLED dates list (dd-mm-YYYY) for the month containing 'date'."""
    r = sess.post(
        f"{BASE}/{LANG}/hqb-slots-for-month",
        data={"branchId": branch_id, "serviceId": service_id, "date": date_dd_mm_yyyy},
        timeout=25,
    )
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) or []


def slots_for_day(
    sess: requests.Session, branch_id: str, service_id: str, date_dd_mm_yyyy: str
) -> List[Dict[str, str]]:
    r = sess.post(
        f"{BASE}/{LANG}/hqb-slots-for-day",
        data={"branchId": branch_id, "serviceId": service_id, "date": date_dd_mm_yyyy},
        timeout=25,
    )
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) or []


def nearest_day(
    sess: requests.Session, branch_id: str, service_id: str, base_date_dd_mm_yyyy: str = ""
) -> Tuple[Optional[str], List[Dict[str, str]]]:
    r = sess.post(
        f"{BASE}/{LANG}/hqb-nearest-day",
        data={"branchId": branch_id, "serviceId": service_id, "date": base_date_dd_mm_yyyy},
        timeout=25,
    )
    r.raise_for_status()
    j = r.json()
    d = j.get("data") or {}
    return d.get("day"), d.get("slots", []) or []


def register(
    sess: requests.Session,
    branch_id: str,
    service_id: str,
    date_dd_mm_yyyy: str,
    slot_time_hh_mm: str,
    email: str,
) -> Dict[str, Any]:
    r = sess.post(
        f"{BASE}/{LANG}/hqb-register",
        data={
            "branchId": branch_id,
            "serviceId": service_id,
            "date": date_dd_mm_yyyy,
            "slotTime": slot_time_hh_mm,
            "email": email,
        },
        timeout=25,
    )
    r.raise_for_status()
    return r.json()


def history(sess: requests.Session) -> List[Dict[str, Any]]:
    r = sess.get(f"{BASE}/{LANG}/hqb-history", timeout=25)
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) or []


def detach(sess: requests.Session, internal_id: str) -> Dict[str, Any]:
    r = sess.post(f"{BASE}/{LANG}/hqb-register-detach", data={"internal_id": internal_id}, timeout=25)
    r.raise_for_status()
    return r.json()


# --- SMS login (endpoints may vary by deployment; these are based on site JS) ---
def login_init(sess: requests.Session, psn: str, phone_number: str, country: str = "AM") -> Any:
    r = sess.post(
        f"{BASE}/{LANG}/hqb-sw/login",
        data={"psn": psn, "phone_number": phone_number, "country": country, "login_type": "hqb"},
        timeout=25,
    )
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"ok": True}


def login_verify(sess: requests.Session, psn: str, phone_number: str, token: str, country: str = "AM") -> Any:
    r = sess.post(
        f"{BASE}/{LANG}/hqb-sw/login_token",
        data={"psn": psn, "phone_number": phone_number, "token": token, "country": country, "login_type": "hqb"},
        timeout=25,
    )
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"ok": True}


# ---------- robust fallback scanning ----------
def find_nearest_available(
    sess: requests.Session, branch_id: str, service_id: str, max_days: int = 120
) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Iterate forward day by day:
    - Get disabled dates per month via /hqb-slots-for-month
    - Skip weekends & disabled
    - Query /hqb-slots-for-day, return first date with slots.
    """
    start = datetime.now()
    disabled_cache: Dict[str, set] = {}

    for i in range(max_days):
        d = start + timedelta(days=i)
        if _is_weekend(d):
            continue

        mkey = _month_key(d)
        if mkey not in disabled_cache:
            probe_date = _to_dd_mm_yyyy(d.replace(day=1))
            disabled_list = slots_for_month(sess, branch_id, service_id, probe_date)
            disabled_cache[mkey] = set(disabled_list or [])

        ds = _to_dd_mm_yyyy(d)
        if ds in disabled_cache[mkey]:
            continue

        day_slots = slots_for_day(sess, branch_id, service_id, ds)
        if day_slots:
            return ds, day_slots

    return None, []
