from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import re, os, time
from datetime import datetime

# Mapping of Armenian month names to month number
ARMENIAN_MONTHS = {
    "հունվար": 1,
    "փետրվար": 2,
    "մարտ": 3,
    "ապրիլ": 4,
    "մայիս": 5,
    "հունիս": 6,
    "հուլիս": 7,
    "օգոստոս": 8,
    "սեպտեմբեր": 9,
    "հոկտեմբեր": 10,
    "նոյեմբեր": 11,
    "դեկտեմբեր": 12
}

def fetch_available_slots(branch: str, exam_type: str, weekday: int=None, specific_date: str=None, specific_hour: str=None) -> str:
    """
    Launch headless Chrome to fetch available exam slots for given branch and exam type.
    Optional filters: weekday (0=Mon,...6=Sun), specific_date as "dd.mm.yyyy", specific_hour as "HH:MM".
    Returns a formatted string of available slots.
    """
    # Configure Selenium Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Specify binary location from environment or default
    chrome_bin = os.environ.get("CHROME_BIN", "/opt/render/project/.render/chrome/opt/google/chrome/chrome")
    chrome_options.binary_location = chrome_bin
    # Initialize Chrome WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    try:
        driver.get("https://roadpolice.am/hy/hqb")
    except Exception as e:
        # if page fails to load, return an error message
        driver.quit()
        return "Կայքից տվյալները ստանալու ընթացքում սխալ տեղի ունեցավ։"
    # The page might require some delay to fully render
    time.sleep(2)
    # Select the branch from dropdown
    try:
        # Try selecting by visible text matching branch name
        option = driver.find_element(By.XPATH, f"//option[contains(normalize-space(text()), '{branch}')]")
        option.click()
    except Exception as e:
        driver.quit()
        return "Բաժանմունքի ընտրությունը կատարվել չի կարող։"
    # Select exam type (theoretical/practical)
    try:
        exam_keyword = "Տեսական" if "տեսական" in exam_type.lower() else "Գործնական"
        exam_label = driver.find_element(By.XPATH, f"//label[contains(text(), '{exam_keyword}')]")
        exam_label.click()
    except Exception as e:
        # In case exam type options are a select element instead of radio
        try:
            exam_select = driver.find_element(By.XPATH, "//select[contains(@name, 'examType')]")
            exam_option = exam_select.find_element(By.XPATH, f".//option[contains(text(), '{exam_keyword}')]")
            exam_option.click()
        except Exception:
            driver.quit()
            return "Քննության տեսակի ընտրությունը կատարվել չի կարող։"
    time.sleep(1)
    results = {}  # dict to accumulate slots by date
    # Loop through months up to a limit
    months_checked = 0
    max_months = 12
    while months_checked < max_months:
        # Get current month-year from calendar header
        month_year_text = ""
        try:
            header = driver.find_element(By.XPATH, "//div[contains(@class, 'calendar') or contains(@class, 'picker') or contains(@class, 'datepicker')]//th[contains(@class, 'month') or contains(@class, 'picker-switch') or contains(@class, 'title')]")
            month_year_text = header.text
        except Exception:
            try:
                header = driver.find_element(By.XPATH, "//div[contains(@class, 'datepicker') or contains(@class, 'calendar')]//span[contains(@class,'Month') or contains(@class,'month')]")
                month_year_text = header.text
            except Exception:
                month_year_text = ""
        # Parse month and year
        curr_year = datetime.now().year
        curr_month = None
        if month_year_text:
            # Example: "Օգոստոս 2025"
            parts = month_year_text.split()
            if len(parts) >= 2:
                month_name = parts[0].lower()
                if month_name in ARMENIAN_MONTHS:
                    curr_month = ARMENIAN_MONTHS[month_name]
                try:
                    curr_year = int(parts[-1])
                except:
                    pass
        # Find all clickable day elements (anchors) in the current month
        day_elems = driver.find_elements(By.XPATH, "//td//a")
        if not day_elems:
            # No available days in this month, go to next month if possible
            try:
                next_btn = driver.find_element(By.XPATH, "//a[@title='Next' or contains(@class,'next')]")
                next_btn.click()
                time.sleep(0.5)
                months_checked += 1
                continue
            except Exception:
                break  # no next button, break out
        # Iterate through each available day in this month
        for idx in range(len(day_elems)):
            # Re-locate the element by index each time (since DOM may update)
            try:
                day_link = driver.find_elements(By.XPATH, "//td//a")[idx]
            except Exception:
                break
            day_text = day_link.text.strip()
            if not day_text.isdigit():
                continue
            day_num = int(day_text)
            # Construct date string
            if curr_month is None:
                # If month couldn't be determined, use current iteration's month from system (fallback)
                curr_month = datetime.now().month
            date_str = f"{day_num:02d}.{curr_month:02d}.{curr_year}"
            # If date filter is applied and this date doesn't match, skip fetching times
            if specific_date and date_str != specific_date:
                continue
            # If weekday filter applied and this date's weekday doesn't match, skip
            if weekday is not None:
                # Compute weekday of this date (Mon=0,...Sun=6)
                try:
                    d = datetime.strptime(date_str, "%d.%m.%Y")
                except Exception:
                    d = None
                if d is None or d.weekday() != weekday:
                    continue
            # Click the day to load times
            try:
                driver.execute_script("arguments[0].click();", day_link)
            except Exception:
                try:
                    day_link.click()
                except:
                    continue
            time.sleep(0.5)
            # Gather available times for this date
            times = []
            # Try to find options in a select
            time_options = driver.find_elements(By.XPATH, "//option[contains(text(), ':')]")
            if time_options:
                for opt in time_options:
                    t = opt.text.strip()
                    if t and re.match(r'\d{2}:\d{2}', t):
                        times.append(t)
            else:
                # Try labels or buttons containing times
                time_labels = driver.find_elements(By.XPATH, "//label[contains(text(), ':')]")
                for lbl in time_labels:
                    t = lbl.text.strip()
                    if t and re.match(r'\d{2}:\d{2}', t):
                        times.append(t)
                if not times:
                    # Possibly times listed as text nodes in clickable elements
                    time_elems = driver.find_elements(By.XPATH, "//*[contains(text(), ':')]")
                    for elem in time_elems:
                        t = elem.text.strip()
                        if re.fullmatch(r'\d{2}:\d{2}', t):
                            times.append(t)
            # Filter times by specific_hour if given
            if specific_hour:
                times = [t for t in times if t == specific_hour]
            if times:
                results[date_str] = sorted(set(times))
        # Move to next month
        try:
            next_btn = driver.find_element(By.XPATH, "//a[@title='Next' or contains(@class,'next')]")
            next_btn.click()
            time.sleep(0.5)
            months_checked += 1
        except Exception:
            break
    driver.quit()
    # Format results
    if not results:
        return "Ազատ ժամեր մատչելի չեն տվյալ արտադրված պայմաններով։"
    # Sort by date
    sorted_dates = sorted(results.keys(), key=lambda d: datetime.strptime(d, "%d.%m.%Y"))
    output_lines = []
    for d in sorted_dates:
        times_list = ", ".join(sorted(results[d]))
        output_lines.append(f"{d}: {times_list}")
    return "\n".join(output_lines)
