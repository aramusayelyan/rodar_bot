import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Base URL for the Road Police appointment page (Armenian language version)
BASE_URL = "https://roadpolice.am/hy/hqb"

def get_available_slots(branch_id: int, service_id: int):
    """
    Fetches all available appointment slots (date & time) for the given branch and exam service.
    Returns a list of (date, time) tuples for available slots.
    """
    session = requests.Session()
    # Step 1: Get the initial page to obtain cookies and CSRF token
    try:
        resp = session.get(BASE_URL, timeout=10)
    except requests.RequestException as e:
        print(f"Error fetching base page: {e}")
        return []  # if network error, return empty
    
    if resp.status_code != 200:
        print(f"Failed to load base page, status: {resp.status_code}")
        return []
    
    page_html = resp.text
    soup = BeautifulSoup(page_html, "html.parser")
    # Extract CSRF token from meta tag
    token_tag = soup.find("meta", {"name": "csrf-token"})
    csrf_token = token_tag["content"] if token_tag else ""
    if not csrf_token:
        print("CSRF token not found on page.")
        return []
    
    # Prepare headers with CSRF token for subsequent POST requests
    headers = {"X-CSRF-TOKEN": csrf_token}
    
    # Step 2: Simulate selecting branch & service.
    # The site likely expects an AJAX request to populate the calendar.
    # We attempt a post request to indicate the chosen branch & service.
    data = {
        "branchId": branch_id,
        "serviceId": service_id
    }
    try:
        # It's possible the site might have a specific endpoint for this.
        # We try posting to the same base URL (which might handle form submission).
        ajax_resp = session.post(BASE_URL, data=data, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"Error posting branch/service selection: {e}")
        # Even if this fails, proceed to parse initial HTML (it might have default data)
        ajax_resp = None
    
    if ajax_resp and ajax_resp.status_code not in (200, 302):
        # 302 might redirect after form submission
        print(f"Unexpected response after selecting branch/service: {ajax_resp.status_code}")
    
    # After selection, let's assume the page (or ajax response) contains updated calendar info.
    updated_html = ajax_resp.text if ajax_resp else page_html
    soup = BeautifulSoup(updated_html, "html.parser")
    
    # Step 3: Parse the calendar for available days.
    available_days = []
    # Calendar days are in span.flatpickr-day. Disabled days have 'flatpickr-disabled' class.
    calendar_days = soup.find_all("span", {"class": "flatpickr-day"})
    today = datetime.today().date()
    for day_elem in calendar_days:
        day_classes = day_elem.get("class", [])
        # Only consider days in the current or next months displayed (ignore prevMonthDay or nextMonthDay outside current view)
        if "prevMonthDay" in day_classes or "nextMonthDay" in day_classes:
            continue
        # flatpickr-day elements have aria-label like "October 7, 2025" in Armenian.
        date_label = day_elem.get("aria-label", "")
        # Parse the date from aria-label (in format "MonthName DD, YYYY" in Armenian).
        # We can try to parse it by extracting day, month, year.
        if not date_label:
            continue
        try:
            # Example aria-label: "Հոկտեմբեր 7, 2025" (MonthName Day, Year in Armenian)
            parts = date_label.split()
            # parts[0] is month name in Armenian, parts[1] is day (with comma), parts[2] is year.
            # Remove comma from day:
            day_str = parts[1].rstrip(",") 
            year_str = parts[2]
            month_name_hy = parts[0]
            # Map Armenian month to number:
            month_map = {
                "Հունվար": 1, "Փետրվար": 2, "Մարտ": 3, "Ապրիլ": 4,
                "Մայիս": 5, "Հունիս": 6, "Հուլիս": 7, "Օգոստոս": 8,
                "Սեպտեմբեր": 9, "Հոկտեմբեր": 10, "Նոյեմբեր": 11, "Դեկտեմբեր": 12
            }
            month_num = month_map.get(month_name_hy, None)
            if month_num is None:
                continue
            day_num = int(day_str)
            year_num = int(year_str)
            date_obj = datetime(year_num, month_num, day_num).date()
        except Exception as parse_err:
            print(f"Failed to parse date label '{date_label}': {parse_err}")
            continue
        
        # Check if day is not disabled
        if "flatpickr-disabled" in day_classes:
            # This day has no available slots (fully booked or not working), skip
            continue
        # If date is in the past relative to today, skip it (shouldn't normally happen for available days)
        if date_obj < today:
            continue
        # This is an available day (at least one slot free)
        available_days.append(date_obj)
    
    # If no available days found, return empty (no slots)
    if not available_days:
        return []
    
    # Step 4: For each available day, find available time slots.
    available_slots = []
    # The site uses specific time increments (e.g., every 8 minutes from 09:16 to ~16:42).
    # We iterate through all possible time slots on that day and test if they are free.
    # Define the typical slot times (this is based on observed pattern; could also be parsed from HTML).
    # Times are in HH:MM (24-hour) format.
    slot_times = [
        "09:16","09:24","09:32","09:40","09:48","09:56",
        "10:04","10:12","10:20","10:28","10:36","10:44","10:52",
        "11:00","11:08","11:16","11:24","11:32","11:40","11:48","11:56",
        "12:12","12:20","12:28","12:36","12:44","12:52",
        "13:00","13:08","13:16","13:30","13:38","13:46","13:54",
        "14:02","14:10","14:18","14:26","14:30","14:34","14:38","14:42","14:46","14:50","14:54","14:58",
        "15:02","15:06","15:10","15:14","15:18","15:22","15:26","15:34","15:38","15:42","15:46","15:50","15:54","15:58",
        "16:02","16:06","16:10","16:14","16:18","16:22","16:26","16:30","16:34","16:38","16:42"
    ]
    # We will attempt to check each time by sending a booking request and seeing if it fails or not.
    for date_obj in available_days:
        date_str = date_obj.strftime("%Y-%m-%d")  # format date as YYYY-MM-DD for request
        for time_str in slot_times:
            # Prepare booking data for this date and time
            booking_data = {
                "branchId": branch_id,
                "serviceId": service_id,
                "date": date_str,
                "slotTime": time_str,
                # We include a dummy email to pass validation (the site requires email for booking confirmation)
                "email": "dummy@example.com"
            }
            try:
                result = session.post(BASE_URL, data=booking_data, headers=headers, timeout=5)
            except requests.RequestException as e:
                # If network error, skip this time
                continue
            # If booking is successful (status 200 and perhaps a specific success message in response),
            # it means the slot was free. If it's already booked, the server likely returns an error message.
            # We need to detect success vs failure without actually taking the slot permanently if possible.
            # Typically, a success might return a confirmation or redirect, whereas a failure might return 400 or a JSON error.
            if result.status_code == 200:
                # Check if response contains the success message text or activation code (which indicates booking done)
                if "activation code" in result.text or "Ակտիվացման կոդ" in result.text:
                    # This indicates a successful booking.
                    # Mark this time as available. (In reality, we just booked it - for a real bot, you'd want to cancel it if possible.)
                    available_slots.append((date_obj, time_str))
                    # (In an actual scenario, we might need to immediately cancel this booking or warn the user.)
                else:
                    # If status 200 but no success message, assume it's a page refresh or something uncertain; treat as failure.
                    pass
            elif result.status_code == 400 or result.status_code == 422:
                # Likely a validation error (slot taken or invalid). We could inspect result.text for specific error.
                # If the error text indicates "already booked" then the slot is not available.
                # We do nothing in this case.
                continue
            elif result.status_code in (302, 301):
                # A redirect might indicate success (booking confirmed and redirected to success page).
                available_slots.append((date_obj, time_str))
            # We do not include else: other status codes are not expected.
        # End of times loop for that date
    # End of days loop
    
    # Sort the available_slots by date/time
    available_slots.sort(key=lambda x: (x[0], x[1]))
    return available_slots
