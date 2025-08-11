# -*- coding: utf-8 -*-
import requests
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup

BASE = "https://roadpolice.am"
LANG = "hy"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"

def cookies_to_dict(jar: requests.cookies.RequestsCookieJar) -> Dict[str, str]:
    return {c.name: c.value for c in jar}

def dict_to_cookiejar(cookies: Dict[str, str]) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for k, v in cookies.items():
        jar.set(k, v, domain="roadpolice.am", path="/")
    return jar

def _attach_default_headers(s: requests.Session):
    s.headers.update({
        "User-Agent": UA,
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
    })

def new_session() -> Tuple[requests.Session, str]:
    s = requests.Session()
    _attach_default_headers(s)
    r = s.get(f"{BASE}/{LANG}/hqb", timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    csrf = meta["content"] if meta else ""
    if csrf:
        s.headers["X-CSRF-TOKEN"] = csrf
    return s, csrf

def ensure_session(cookies: Optional[Dict[str, str]] = None) -> Tuple[requests.Session, str]:
    if cookies:
        s = requests.Session()
        _attach_default_headers(s)
        s.cookies = dict_to_cookiejar(cookies)
        r = s.get(f"{BASE}/{LANG}/hqb", timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", attrs={"name": "csrf-token"})
        csrf = meta["content"] if meta else ""
        if csrf:
            s.headers["X-CSRF-TOKEN"] = csrf
        return s, csrf
    return new_session()

def get_branch_and_services(s: requests.Session) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    r = s.get(f"{BASE}/{LANG}/hqb", timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    branches: List[Tuple[str, str]] = []
    services: List[Tuple[str, str]] = []
    bsel = soup.select("select[name='branchId'] option")
    ssel = soup.select("select[name='serviceId'] option")
    for o in bsel:
        if o.get("value"):
            branches.append((o.text.strip(), o["value"].strip()))
    for o in ssel:
        if o.get("value"):
            services.append((o.text.strip(), o["value"].strip()))
    return branches, services

def slots_for_month(sess: requests.Session, branch_id: str, service_id: str, date_dd_mm_yyyy: str) -> List[str]:
    r = sess.post(f"{BASE}/{LANG}/hqb-slots-for-month",
                  data={"branchId": branch_id, "serviceId": service_id, "date": date_dd_mm_yyyy},
                  timeout=25)
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) or []

def slots_for_day(sess: requests.Session, branch_id: str, service_id: str, date_dd_mm_yyyy: str) -> List[Dict[str, str]]:
    r = sess.post(f"{BASE}/{LANG}/hqb-slots-for-day",
                  data={"branchId": branch_id, "serviceId": service_id, "date": date_dd_mm_yyyy},
                  timeout=25)
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) or []

def nearest_day(sess: requests.Session, branch_id: str, service_id: str, base_date_dd_mm_yyyy: str = "") -> Tuple[Optional[str], List[Dict[str, str]]]:
    r = sess.post(f"{BASE}/{LANG}/hqb-nearest-day",
                  data={"branchId": branch_id, "serviceId": service_id, "date": base_date_dd_mm_yyyy},
                  timeout=25)
    r.raise_for_status()
    j = r.json()
    d = j.get("data") or {}
    return d.get("day"), d.get("slots", []) or []

def register(sess: requests.Session, branch_id: str, service_id: str, date_dd_mm_yyyy: str, slot_time_hh_mm: str, email: str) -> Dict[str, Any]:
    r = sess.post(f"{BASE}/{LANG}/hqb-register",
                  data={"branchId": branch_id, "serviceId": service_id, "date": date_dd_mm_yyyy,
                        "slotTime": slot_time_hh_mm, "email": email},
                  timeout=25)
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

def login_init(sess: requests.Session, psn: str, phone_number: str, country: str = "AM") -> Any:
    r = sess.post(f"{BASE}/{LANG}/hqb-sw/login",
                  data={"psn": psn, "phone_number": phone_number, "country": country, "login_type": "hqb"},
                  timeout=25)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"ok": True}

def login_verify(sess: requests.Session, psn: str, phone_number: str, token: str, country: str = "AM") -> Any:
    r = sess.post(f"{BASE}/{LANG}/hqb-sw/login_token",
                  data={"psn": psn, "phone_number": phone_number, "token": token, "country": country, "login_type": "hqb"},
                  timeout=25)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"ok": True}
