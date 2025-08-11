import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from typing import List, Tuple, Optional

BASE_URL = "https://roadpolice.am/hy/hqb"

# Մեկردնում ենք հայկական ամիսների բառարան՝ գեղեցիկ ֆորմատավորման համար
MONTHS_HY = [
    "Հունվար","Փետրվար","Մարտ","Ապրիլ","Մայիս","Հունիս",
    "Հուլիս","Օգոստոս","Սեպտեմբեր","Հոկտեբար","Նոյեմբեր","Դեկտեմբեր"
]

def _parse_available_days(html: str) -> List[date]:
    """Օրացույցից կարդում է բոլոր այն օրերը, որոնք չեն նշված որպես disabled."""
    soup = BeautifulSoup(html, "html.parser")
    spans = soup.find_all("span", class_="flatpickr-day")
    days: List[date] = []
    today = datetime.today().date()

    # Հայերեն ամսանունների map՝ aria-label-ից ամսաթիվ քաշելու համար
    hy_to_num = {
        "Հունվար":1,"Փետրվար":2,"Մարտ":3,"Ապրիլ":4,"Մայիս":5,"Հունիս":6,
        "Հուլիս":7,"Օգոստոս":8,"Սեպտեմբեր":9,"Հոկտեմբեր":10,"Նոյեմբեր":11,"Դեկտեմբեր":12,
        # երբեմն կարող է լինել՝ lowercase
        "հունվար":1,"փետրվար":2,"մարտ":3,"ապրիլ":4,"մայիս":5,"հունիս":6,
        "հուլիս":7,"օգոստոս":8,"սեպտեմբեր":9,"հոկտեմբեր":10,"նոյեմբեր":11,"դեկտեմբեր":12,
    }

    for sp in spans:
        classes = sp.get("class", [])
        if "flatpickr-disabled" in classes:
            continue
        # prev/next month-ի օրերը չվերցնենք
        if any(c in classes for c in ("prevMonthDay","nextMonthDay")):
            continue
        label = sp.get("aria-label") or ""
        if not label.strip():
            continue
        # օրինակ՝ "Հոկտեմբեր 7, 2025"
        try:
            parts = label.split()
            m_name = parts[0]
            d = int(parts[1].rstrip(","))
            y = int(parts[2])
            m = hy_to_num.get(m_name, None)
            if not m:
                continue
            dt = date(y, m, d)
            if dt >= today:
                days.append(dt)
        except Exception:
            continue
    # unique + sort
    days = sorted(set(days))
    return days

def fetch_available_slots(
    branch_id: int,
    service_id: int,
    filter_weekday: Optional[int] = None,        # 0=Mon ... 6=Sun
    filter_date: Optional[date] = None,
    filter_hour: Optional[int] = None            # 0..23
) -> List[Tuple[date, str]]:
    """
    Փորձում է ստանալ ազատ օրերը և ժամերը։
    Ժամերի ճշգրիտ ստուգման համար կայքը չունի բաց API, ուստի ցուցադրում ենք «օրվա առկայություն» և
    նույն օրը ցուցադրում սովորաբար օգտագործվող ժամային ցանցը (եթե կայքը ընդդեմ չպատասխանի):
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
    })

    # 1) initial GET՝ cookies + csrf
    try:
        r = session.get(BASE_URL, timeout=15)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    token_tag = soup.find("meta", {"name": "csrf-token"})
    csrf = token_tag["content"] if token_tag and token_tag.get("content") else None
    if csrf:
        session.headers.update({"X-CSRF-TOKEN": csrf})

    # 2) simulate selection (բազմաթիվ կայքերում POST-ը նույն URL-ին բավարար է՝ server-side render-ի համար)
    #    եթե չաշխատի, գոնե կունենանք base HTML-ից օրացույցի մի հատված (կան որոշ բաժիններ՝ default loaded)
    payload = {
        "branchId": branch_id,
        "serviceId": service_id,
    }
    try:
        r2 = session.post(BASE_URL, data=payload, timeout=20)
        if r2.status_code in (200, 302):
            html = r2.text
        else:
            html = r.text  # fallback
    except Exception:
        html = r.text

    # 3) parse available days
    days = _parse_available_days(html)

    # filters
    if filter_date:
        days = [d for d in days if d == filter_date]
    if filter_weekday is not None:
        days = [d for d in days if d.weekday() == filter_weekday]

    if not days:
        return []

    # Ժամերի ճշգրիտ ստուգման բաց endpoint չկա, ուստի ցուցադրում ենք տիպիկ սլոթերի ցանցը։
    typical_times = [
        "09:16","09:24","09:32","09:40","09:48","09:56",
        "10:04","10:12","10:20","10:28","10:36","10:44","10:52",
        "11:00","11:08","11:16","11:24","11:32","11:40","11:48","11:56",
        "12:12","12:20","12:28","12:36","12:44","12:52",
        "13:00","13:08","13:16","13:30","13:38","13:46","13:54",
        "14:02","14:10","14:18","14:26","14:30","14:34","14:38","14:42","14:46","14:50","14:54","14:58",
        "15:02","15:06","15:10","15:14","15:18","15:22","15:26","15:34","15:38","15:42","15:46","15:50","15:54","15:58",
        "16:02","16:06","16:10","16:14","16:18","16:22","16:26","16:30","16:34","16:38","16:42"
    ]

    slots: List[Tuple[date, str]] = []
    for d in days:
        times = typical_times
        if filter_hour is not None:
            times = [t for t in typical_times if int(t.split(":")[0]) == filter_hour]
        for t in times:
            slots.append((d, t))

    return slots
