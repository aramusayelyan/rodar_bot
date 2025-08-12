import logging
import re
from typing import Dict, List, Tuple, Optional
import requests
from urllib.parse import unquote
from bs4 import BeautifulSoup
import config

logger = logging.getLogger(__name__)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (X11; Linux) AppleWebKit/537.36 (KHTML, like Gecko) PTB/13 Safari/537.36",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": config.RP_BASE,
    "Referer": f"{config.RP_BASE}/{config.RP_LANG}",
}

def _read_xsrf_token(session: requests.Session) -> Optional[str]:
    token_cookie = session.cookies.get("XSRF-TOKEN")
    if not token_cookie:
        return None
    try:
        return unquote(token_cookie)
    except Exception:
        return token_cookie

def _post(session: requests.Session, path: str, data: Dict[str, str]) -> Dict:
    xsrf = _read_xsrf_token(session)
    headers = dict(HEADERS_BASE)
    if xsrf:
        headers["x-csrf-token"] = xsrf
    url = f"{config.RP_BASE}/{config.RP_LANG}/{path}"
    r = session.post(url, data=data, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

def init_session(seed_cookies: Optional[Dict[str, str]] = None) -> requests.Session:
    s = requests.Session()
    s.get(f"{config.RP_BASE}/{config.RP_LANG}", headers=HEADERS_BASE, timeout=20)
    s.get(f"{config.RP_BASE}/{config.RP_LANG}/hqb", headers=HEADERS_BASE, timeout=20)
    if seed_cookies:
        for k, v in seed_cookies.items():
            s.cookies.set(k, v, domain="roadpolice.am", secure=True)
    _ = _read_xsrf_token(s)
    return s

def login(session: requests.Session, psn: str, phone: str, country: str = "374") -> Dict:
    payload = {"psn": psn, "phone_number": phone, "country": country}
    return _post(session, "hqb-sw/login", payload)

def verify(session: requests.Session, token: str) -> Dict:
    return _post(session, "hqb-sw/verify", {"token": token})

def fetch_branches_and_services(session: requests.Session) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    url = f"{config.RP_BASE}/{config.RP_LANG}/hqb"
    r = session.get(url, headers=HEADERS_BASE, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    def parse_select(name: str) -> List[Tuple[str, str]]:
        sel = soup.select_one(f'select[name="{name}"]')
        items: List[Tuple[str, str]] = []
        if sel:
            for opt in sel.find_all("option"):
                val = (opt.get("value") or "").strip()
                txt = (opt.text or "").strip()
                if not val or not txt:
                    continue
                items.append((val, txt))
        return items

    branches = parse_select("branchId")
    services = parse_select("serviceId")
    return branches, services

def nearest_day(session: requests.Session, branch_id: str, service_id: str, from_date_dd_mm_yyyy: str) -> Dict:
    return _post(session, "hqb-nearest-day", {
        "branchId": branch_id, "serviceId": service_id, "date": from_date_dd_mm_yyyy
    })

def slots_for_day(session: requests.Session, branch_id: str, service_id: str, date_dd_mm_yyyy: str) -> List[Dict]:
    resp = _post(session, "hqb-slots-for-day", {
        "branchId": branch_id, "serviceId": service_id, "date": date_dd_mm_yyyy
    })
    return resp.get("data") or []

def register_slot(session: requests.Session, branch_id: str, service_id: str,
                  date_dd_mm_yyyy: str, slot_time: str, email: str) -> Dict:
    return _post(session, "hqb-register", {
        "branchId": branch_id, "serviceId": service_id,
        "date": date_dd_mm_yyyy, "slotTime": slot_time, "email": email
    })
