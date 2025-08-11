# scraper.py
import re
import requests
from datetime import datetime, timedelta

# Dictionary to store active sessions per user
sessions = {}

def get_session(user_id: int):
    """Get or create a requests Session for a user."""
    if user_id not in sessions:
        sessions[user_id] = requests.Session()
    return sessions[user_id]

def login_send_code(user_id: int, psn: str, phone: str) -> bool:
    """
    Start the login process by sending an SMS code.
    Returns True if code sent, False if failed.
    """
    sess = get_session(user_id)
    # Get the homepage to obtain CSRF token and cookies
    url_home = "https://roadpolice.am/hy"
    res = sess.get(url_home)
    if res.status_code != 200:
        return False
    # Extract CSRF token from HTML
    text = res.text
    m = re.search(r'name="csrf-token" content="([^"]+)"', text)
    if not m:
        return False
    csrf_token = m.group(1)
    # Set CSRF header for subsequent requests
    sess.headers.update({"X-CSRF-TOKEN": csrf_token, "X-Requested-With": "XMLHttpRequest"})
    # Normalize phone number format (Armenian)
    phone_digits = phone
    if phone_digits.startswith('+'):
        phone_digits = phone_digits[1:]
    if phone_digits.startswith('0'):
        phone_digits = '374' + phone_digits[1:]
    # Data payload for requesting SMS code
    data = {
        "publicServiceNumber": psn,
        "phoneNumber": phone_digits
    }
    # Send request to trigger SMS code
    send_url = "https://roadpolice.am/hy/send-code"
    res2 = sess.post(send_url, data=data)
    if res2.status_code != 200:
        return False
    try:
        resp_json = res2.json()
        if isinstance(resp_json, dict) and resp_json.get("error"):
            return False
    except Exception:
        pass
    return True

def login_verify_code(user_id: int, psn: str, phone: str, code: str) -> bool:
    """
    Complete login by verifying the SMS code.
    Returns True if login successful, False otherwise.
    """
    sess = get_session(user_id)
    # Prepare phone in same format as send_code
    phone_digits = phone
    if phone_digits.startswith('+'):
        phone_digits = phone_digits[1:]
    if phone_digits.startswith('0'):
        phone_digits = '374' + phone_digits[1:]
    data = {
        "publicServiceNumber": psn,
        "phoneNumber": phone_digits,
        "smsCode": code
    }
    verify_url = "https://roadpolice.am/hy/verify-code"
    res = sess.post(verify_url, data=data)
    if res.status_code != 200:
        return False
    # Verify by checking if /hqb is accessible (which requires auth)
    test_res = sess.get("https://roadpolice.am/hy/hqb")
    if test_res.status_code != 200:
        return False
    return True

def ensure_logged_in(user_id: int, cookies: dict) -> requests.Session:
    """
    Ensure the session for user is logged in (using stored cookies).
    Returns a Session object if successful, otherwise raises Exception.
    """
    sess = get_session(user_id)
    # Load cookies into session
    sess.cookies.clear()
    for name, value in cookies.items():
        sess.cookies.set(name, value)
    # Access a protected page to confirm login and refresh CSRF token
    res = sess.get("https://roadpolice.am/hy/hqb")
    if res.status_code != 200:
        raise Exception("Session invalid or expired")
    m = re.search(r'name="csrf-token" content="([^"]+)"', res.text)
    if m:
        csrf_token = m.group(1)
        sess.headers.update({"X-CSRF-TOKEN": csrf_token, "X-Requested-With": "XMLHttpRequest"})
    return sess

def fetch_available_days(user_id: int, cookies: dict, branch_id: str, service_id: str, year: int, month: int):
    """
    Fetch available days in the given month that have at least one slot.
    Returns a list of date strings 'YYYY-MM-DD' that have free slots.
    """
    sess = ensure_logged_in(user_id, cookies)
    url = "https://roadpolice.am/hy/hqb-slots-for-month"
    params = {"branchId": branch_id, "serviceId": service_id, "year": year, "month": month}
    res = sess.get(url, params=params)
    if res.status_code != 200:
        raise Exception("Failed to fetch slots for month")
    data = res.json()
    available_days = []
    if isinstance(data, list):
        available_days = data
    elif isinstance(data, dict):
        if "freeDates" in data:
            available_days = data["freeDates"]
        elif "availableDates" in data:
            available_days = data["availableDates"]
        elif "busyDates" in data:
            busy = set(data["busyDates"])
            first_day = datetime(year, month, 1)
            if month == 12:
                next_month = datetime(year+1, 1, 1)
            else:
                next_month = datetime(year, month+1, 1)
            last_day = next_month - timedelta(days=1)
            date_iter = first_day
            while date_iter <= last_day:
                date_str = date_iter.strftime("%Y-%m-%d")
                if date_str not in busy:
                    available_days.append(date_str)
                date_iter += timedelta(days=1)
    return sorted(available_days)

def fetch_available_times(user_id: int, cookies: dict, branch_id: str, service_id: str, date_str: str):
    """
    Fetch available time slots for a specific date.
    Returns a list of time strings 'HH:MM' that are available.
    """
    sess = ensure_logged_in(user_id, cookies)
    url = "https://roadpolice.am/hy/hqb-slots-for-day"
    params = {"branchId": branch_id, "serviceId": service_id, "date": date_str}
    res = sess.get(url, params=params)
    if res.status_code != 200:
        raise Exception("Failed to fetch slots for day")
    data = res.json()
    times = []
    if isinstance(data, list):
        times = data
    elif isinstance(data, dict):
        if "freeTimes" in data:
            times = data["freeTimes"]
        elif "availableSlots" in data:
            times = data["availableSlots"]
    return times

def book_appointment(user_id: int, cookies: dict, branch_id: str, service_id: str, date_str: str, time_str: str, email: str) -> bool:
    """
    Book an appointment (queue ticket) for the given service, branch, date, and time.
    Returns True if booking successful, False otherwise.
    """
    sess = ensure_logged_in(user_id, cookies)
    url = "https://roadpolice.am/hy/hqb-license-request"
    data = {
        "serviceId": service_id,
        "branchId": branch_id,
        "date": date_str,
        "slotTime": time_str,
        "email": email
    }
    res = sess.post(url, data=data)
    if res.status_code != 200:
        return False
    try:
        resp_json = res.json()
        if isinstance(resp_json, dict) and resp_json.get("error"):
            return False
    except Exception:
        pass
    return True
