import calendar
import json
import logging
import re
import urllib.parse
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger(__name__)

BASE = config.RP_BASE
LANG = config.RP_LANG
TIMEOUT = config.REQUEST_TIMEOUT
UA = config.USER_AGENT

def _new_session(cookies: Optional[Dict[str, Any]] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "hy-AM,hy;q=0.9,en-US;q=0.6,en;q=0.5",
        "X-Requested-With": "XMLHttpRequest",
    })
    if cookies:
        # restore stored cookies
        for k, v in cookies.items():
            s.cookies.set(k, v, domain="roadpolice.am", secure=True)
    return s

def _ensure_csrf_from_cookie(s: requests.Session):
    if "X-CSRF-TOKEN" not in s.headers:
        xsrf = s.cookies.get("XSRF-TOKEN")
        if xsrf:
            try:
                s.headers["X-CSRF-TOKEN"] = urllib.parse.unquote(xsrf)
            except Exception:
                s.headers["X-CSRF-TOKEN"] = xsrf

def _load_csrf(s: requests.Session) -> str:
    # try /hy first
    r = s.get(f"{BASE}/{LANG}", timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    token = meta["content"] if meta else ""
    if not token:
        r2 = s.get(f"{BASE}/{LANG}/hqb", timeout=TIMEOUT)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")
        meta2 = soup2.find("meta", attrs={"name": "csrf-token"})
        token = meta2["content"] if meta2 else ""
    if token:
        s.headers["X-CSRF-TOKEN"] = token
    else:
        _ensure_csrf_from_cookie(s)
    return s.headers.get("X-CSRF-TOKEN", "")

def _serialize_cookies(s: requests.Session) -> Dict[str, str]:
    jar = {}
    for c in s.cookies:
        if c.domain.endswith("roadpolice.am"):
            jar[c.name] = c.value
    return jar

def normalize_phone_to_local(phone: str) -> str:
    p = re.sub(r"\D", "", phone)
    # strip leading country code 374 or +374
    if p.startswith("374"):
        p = p[3:]
    if p.startswith("0"):
        p = p[1:]
    return p

# -------- Login flow ----------

def login_init(sess: requests.Session, psn: str, phone: str, country: str = "AM") -> Dict[str, Any]:
    if "X-CSRF-TOKEN" not in sess.headers:
        _load_csrf(sess)
    _ensure_csrf_from_cookie(sess)
    headers = {"Referer": f"{BASE}/{LANG}"}
    data = {"psn": psn, "phone_number": phone, "country": country, "login_type": "hqb"}
    r = sess.post(f"{BASE}/{LANG}/hqb-sw/login", headers=headers, data=data, timeout=TIMEOUT)
    if r.status_code >= 400:
        # fallback with numeric country code
        data["country"] = "374"
        r = sess.post(f"{BASE}/{LANG}/hqb-sw/login", headers=headers, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"ok": True}

def login_verify(sess: requests.Session, psn: str, phone: str, token: str, country: str = "AM") -> Dict[str, Any]:
    if "X-CSRF-TOKEN" not in sess.headers:
        _load_csrf(sess)
    _ensure_csrf_from_cookie(sess)
    headers = {"Referer": f"{BASE}/{LANG}"}
    data = {"psn": psn, "phone_number": phone, "token": token, "country": country, "login_type": "hqb"}
    r = sess.post(f"{BASE}/{LANG}/hqb-sw/login_token", headers=headers, data=data, timeout=TIMEOUT)
    if r.status_code >= 400:
        data["country"] = "374"
        r = sess.post(f"{BASE}/{LANG}/hqb-sw/login_token", headers=headers, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"ok": True}

# -------- Parsing helpers ----------

def _parse_select_options(soup: BeautifulSoup, select_name: str) -> List[Dict[str, str]]:
    sel = soup.select_one(f"select[name='{select_name}']")
    out = []
    if not sel:
        return out
    for opt in sel.find_all("option"):
        val = (opt.get("value") or "").strip()
        label = (opt.text or "").strip()
        if not val:
            continue
        out.append({"id": val, "label": label})
    return out

def fetch_services_branches(sess: requests.Session) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    r = sess.get(f"{BASE}/{LANG}/hqb", timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    services = _parse_select_options(soup, "serviceId")
    branches = _parse_select_options(soup, "branchId")
    return services, branches

# -------- Slots / Register ----------

def slots_for_month(sess: requests.Session, branch_id: str, service_id: str, day_str: str) -> List[str]:
    """returns disabled dates list from API (format likely 'd-m-Y')."""
    if "X-CSRF-TOKEN" not in sess.headers:
        _load_csrf(sess)
    _ensure_csrf_from_cookie(sess)
    headers = {"Referer": f"{BASE}/{LANG}"}
    data = {"branchId": branch_id, "serviceId": service_id, "date": day_str}
    r = sess.post(f"{BASE}/{LANG}/hqb-slots-for-month", headers=headers, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    js = r.json()
    return js.get("data", []) or []

def slots_for_day(sess: requests.Session, branch_id: str, service_id: str, day_str: str) -> List[Dict[str, str]]:
    if "X-CSRF-TOKEN" not in sess.headers:
        _load_csrf(sess)
    _ensure_csrf_from_cookie(sess)
    headers = {"Referer": f"{BASE}/{LANG}"}
    data = {"branchId": branch_id, "serviceId": service_id, "date": day_str}
    r = sess.post(f"{BASE}/{LANG}/hqb-slots-for-day", headers=headers, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    js = r.json()
    return js.get("data", []) or []

def nearest_day(sess: requests.Session, branch_id: str, service_id: str, ref_date_str: str) -> Optional[Dict[str, Any]]:
    """try API nearest-day, fallback to month/day scan."""
    if "X-CSRF-TOKEN" not in sess.headers:
        _load_csrf(sess)
    _ensure_csrf_from_cookie(sess)
    headers = {"Referer": f"{BASE}/{LANG}"}
    data = {"branchId": branch_id, "serviceId": service_id, "date": ref_date_str}
    r = sess.post(f"{BASE}/{LANG}/hqb-nearest-day", headers=headers, data=data, timeout=TIMEOUT)
    if r.ok:
        js = r.json()
        if js.get("data") and js["data"].get("day"):
            return js["data"]
    # fallback: compute available day and first slots
    # ref_date_str format expected "dd-mm-YYYY"
    d0 = datetime.strptime(ref_date_str, "%d-%m-%Y").date()
    y, m = d0.year, d0.month
    # try current month then next month
    for _ in range(2):
        first_day = date(y, m, 1)
        disabled = set(slots_for_month(sess, branch_id, service_id, first_day.strftime("%d-%m-%Y")))
        # build all working days in month
        _, ndays = calendar.monthrange(y, m)
        candidates = []
        for day in range(1, ndays + 1):
            dt = date(y, m, day)
            if dt.weekday() >= 5:  # 5,6 -> weekend
                continue
            key = dt.strftime("%d-%m-%Y")
            if key in disabled:
                continue
            if dt >= d0:
                candidates.append(dt)
        for dt in candidates:
            slots = slots_for_day(sess, branch_id, service_id, dt.strftime("%d-%m-%Y"))
            if slots:
                return {"day": dt.strftime("%d-%m-%Y"), "slots": slots}
        # move to next month
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        d0 = date(y, m, 1)
    return None

def register_appointment(sess: requests.Session, branch_id: str, service_id: str, day_str: str, slot_value: str, email: str) -> Dict[str, Any]:
    if "X-CSRF-TOKEN" not in sess.headers:
        _load_csrf(sess)
    _ensure_csrf_from_cookie(sess)
    headers = {"Referer": f"{BASE}/{LANG}"}
    data = {
        "branchId": branch_id,
        "serviceId": service_id,
        "date": day_str,
        "slotTime": slot_value,
        "email": email,
    }
    r = sess.post(f"{BASE}/{LANG}/hqb-register", headers=headers, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    js = r.json()
    return js
