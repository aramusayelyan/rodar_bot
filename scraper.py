# -*- coding: utf-8 -*-
import re
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

BASE = "https://roadpolice.am"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119 Safari/537.36",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
}

def _extract_csrf(html: str) -> Optional[str]:
    m = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
    return m.group(1) if m else None

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def ensure_session(cookies: Optional[Dict[str, str]] = None) -> Tuple[requests.Session, Optional[str]]:
    s = _new_session()
    if cookies:
        for k, v in cookies.items():
            s.cookies.set(k, v)
    # load page with csrf
    r = s.get(f"{BASE}/hy/hqb")
    csrf = None
    if r.status_code == 200:
        csrf = _extract_csrf(r.text)
        if csrf:
            s.headers["X-CSRF-TOKEN"] = csrf
    return s, csrf

def login_send_code(psn: str, phone: str) -> Tuple[bool, requests.Session, Optional[str]]:
    s, csrf = ensure_session()
    # normalize phone (strip + and leading 0 -> 374)
    p = phone.strip()
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0"):
        p = "374" + p[1:]
    # Attempt a common auth endpoint pattern (site specific; may vary)
    # If site does not require SMS for viewing slots, this will be a no-op and we still return True with session.
    r = s.post(f"{BASE}/hy/hqb-send-code", data={"publicServiceNumber": psn, "phoneNumber": p})
    if r.status_code == 200:
        try:
            j = r.json()
            if isinstance(j, dict) and j.get("needCode") is False:
                return True, s, csrf
            # otherwise code sent
            return True, s, csrf
        except Exception:
            return True, s, csrf
    # fallback: still return session for slots fetch
    return True, s, csrf

def login_verify_code(sess: requests.Session, psn: str, phone: str, code: str) -> bool:
    p = phone.strip()
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0"):
        p = "374" + p[1:]
    r = sess.post(f"{BASE}/hy/hqb-verify-code", data={"publicServiceNumber": psn, "phoneNumber": p, "smsCode": code})
    if r.status_code == 200:
        return True
    # try to access protected page anyhow
    t = sess.get(f"{BASE}/hy/hqb")
    return (t.status_code == 200)

def get_branches() -> List[Tuple[str, str]]:
    s, _ = ensure_session()
    r = s.get(f"{BASE}/hy/hqb")
    if r.status_code != 200:
        # fallback static
        return [
            ("Երևան", "33"), ("Գյումրի (Շիրակ)", "39"), ("Վանաձոր (Լոռի)", "40"),
            ("Մեծամոր (Արմավիր)", "38"), ("Ակունք (Կոտայք)", "42"), ("Մխչյան (Արարատ)", "44"),
            ("Աշտարակ (Արագածոտն)", "43"), ("Կապան (Սյունիք)", "36"), ("Իջևան (Տավուշ)", "41"),
            ("Սևան (Գեղարքունիք)", "34"), ("Մարտունի (Գեղարքունիք)", "35"),
            ("Գորիս (Սյունիք)", "37"), ("Եղեգնաձոր (Վայոց ձոր)", "45")
        ]
    html = r.text
    # parse options of select name="branchId"
    options = re.findall(r'<select[^>]*name="branchId"[^>]*>(.*?)</select>', html, re.S)
    out: List[Tuple[str, str]] = []
    if options:
        for m in re.findall(r'<option\s+value="(\d+)">([^<]+)</option>', options[0]):
            out.append((m[1].strip(), m[0].strip()))
    if not out:
        # fallback static
        out = [
            ("Երևան", "33"), ("Գյումրի (Շիրակ)", "39"), ("Վանաձոր (Լոռի)", "40"),
            ("Մեծամոր (Արմավիր)", "38"), ("Ակունք (Կոտայք)", "42"), ("Մխչյան (Արարատ)", "44"),
            ("Աշտարակ (Արագածոտն)", "43"), ("Կապան (Սյունիք)", "36"), ("Իջևան (Տավուշ)", "41"),
            ("Սևան (Գեղարքունիք)", "34"), ("Մարտունի (Գեղարքունիք)", "35"),
            ("Գորիս (Սյունիք)", "37"), ("Եղեգնաձոր (Վայոց ձոր)", "45")
        ]
    return out

def fetch_available_days(sess: requests.Session, branch_id: str, service_id: str, year: int, month: int) -> List[str]:
    # POST form-encoded per observed network
    r = sess.post(f"{BASE}/hy/hqb-slots-for-month",
                  data={"branchId": branch_id, "serviceId": service_id, "year": year, "month": month})
    if r.status_code != 200:
        return []
    try:
        j = r.json()
    except Exception:
        return []
    days: List[str] = []
    if isinstance(j, list):
        days = j
    elif isinstance(j, dict):
        days = j.get("freeDates") or j.get("availableDates") or []
    return sorted(days)

def fetch_available_times(sess: requests.Session, branch_id: str, service_id: str, date_iso: str) -> List[str]:
    r = sess.post(f"{BASE}/hy/hqb-slots-for-day",
                  data={"branchId": branch_id, "serviceId": service_id, "date": date_iso})
    if r.status_code != 200:
        return []
    try:
        j = r.json()
    except Exception:
        return []
    times: List[str] = []
    if isinstance(j, list):
        times = j
    elif isinstance(j, dict):
        times = j.get("freeTimes") or j.get("availableSlots") or []
    return times

def find_closest_slot(sess: requests.Session, branch_id: str, service_id: str, from_date: Optional[datetime] = None, months_ahead: int = 3) -> Optional[Tuple[str, str]]:
    now = from_date or datetime.now()
    for mo in range(months_ahead):
        y = now.year + ((now.month - 1 + mo) // 12)
        m = ((now.month - 1 + mo) % 12) + 1
        days = fetch_available_days(sess, branch_id, service_id, y, m)
        for d in days:
            # ensure d >= today
            try:
                # d can be YYYY-MM-DD or DD.MM.YYYY; normalize to YYYY-MM-DD
                if re.match(r"^\d{2}\.\d{2}\.\d{4}$", d):
                    di = datetime.strptime(d, "%d.%m.%Y").strftime("%Y-%m-%d")
                else:
                    di = d
                if di < now.strftime("%Y-%m-%d"):
                    continue
                times = fetch_available_times(sess, branch_id, service_id, di)
                if times:
                    return di, times[0]
            except Exception:
                continue
    return None

def book_appointment(sess: requests.Session, branch_id: str, service_id: str, date_iso: str, time_str: str, email: str) -> bool:
    # Endpoint name may differ; this follows earlier observed patterns
    r = sess.post(f"{BASE}/hy/hqb-license-request",
                  data={"serviceId": service_id, "branchId": branch_id, "date": date_iso, "slotTime": time_str, "email": email})
    if r.status_code != 200:
        return False
    try:
        j = r.json()
        if isinstance(j, dict) and j.get("error"):
            return False
    except Exception:
        pass
    return True
