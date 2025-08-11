from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
import time
import re
import os

# Initialize Chrome options for headless browsing
chrome_options = Options()
# Specify Chrome binary location from environment
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", None)
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def login_start(phone_number: str):
    """
    Start login process on roadpolice.am using mobile ID (phone + SMS).
    Opens the site, enters the phone number and clicks the Login button to trigger SMS code.
    Returns the Selenium WebDriver instance (with session alive for further steps).
    """
    # Launch headless Chrome browser
    service = Service(os.environ.get("CHROMEDRIVER_PATH"))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)  # implicit wait for elements to load
    # Open the Armenian version of roadpolice.am (for correct field labels)
    driver.get("https://roadpolice.am/hy")
    # Find phone number input field and enter the number
    # The phone number is entered without country code, assuming +374 is default
    try:
        # There may be multiple phone inputs (mobile ID login and alternate login).
        # We select the first occurrence of an input for phone.
        phone_input = driver.find_elements(By.CSS_SELECTOR, "input[type='tel']")[0]
    except IndexError:
        raise Exception("Phone input field not found on roadpolice.am")
    phone_input.clear()
    phone_input.send_keys(phone_number)
    # Click the "Մուտք" (Login) button to send SMS code
    # We assume the first button with text "Մուտք" corresponds to mobile login.
    login_buttons = driver.find_elements(By.XPATH, "//*[text()='Մուտք']")
    if not login_buttons:
        raise Exception("Login button not found or page structure changed")
    login_buttons[0].click()
    # After clicking, the SMS code should be sent to the user.
    # The driver remains logged in waiting for code confirmation.
    return driver

def login_verify(driver, code: str) -> bool:
    """
    Enter the SMS code and confirm login. Returns True if login succeeds, otherwise False.
    """
    try:
        # Find SMS code input field (placeholder "ՍՄՍ կոդը") and enter the code
        code_input = driver.find_element(By.XPATH, "//input[@placeholder='ՍՄՍ կոդը']")
    except Exception:
        # If not found by placeholder, try by name "Password" (English placeholder)
        try:
            code_input = driver.find_element(By.NAME, "Password")
        except Exception:
            return False
    code_input.clear()
    code_input.send_keys(code)
    # Click the "Հաստատել" (Confirm) button
    try:
        confirm_btn = driver.find_element(By.XPATH, "//*[text()='Հաստատել']")
    except Exception:
        # If text-based search fails, try input type submit
        confirm_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    confirm_btn.click()
    # Wait for a short time to allow login to process
    time.sleep(3)
    # Check if login was successful by presence of department selection (a <select> element for branches)
    try:
        driver.find_element(By.TAG_NAME, "select")
        return True
    except Exception:
        return False

def get_departments(driver):
    """
    After successful login, scrape the list of available registration-exam subdivisions (branches).
    Returns a list of tuples (branch_name, branch_value) for each option.
    """
    # Wait for the branch selection dropdown to be present
    # (We assume the first <select> element on the page is the branch list)
    selects = driver.find_elements(By.TAG_NAME, "select")
    if not selects:
        raise Exception("Branch selection not found")
    # Identify the select that corresponds to branches by its options
    branch_select = None
    for sel in selects:
        options = sel.find_elements(By.TAG_NAME, "option")
        texts = [opt.text for opt in options]
        # If any option text looks like a region/city or contains "բաժին", assume this is the branch list
        if any("բաժին" in t or "մարզ" in t or "ք." in t for t in texts):
            branch_select = sel
            break
    if branch_select is None:
        # If not identified, default to the first select
        branch_select = selects[0]
    # Extract options (skip any placeholder like "Ընտրեք բաժինը")
    dept_options = []
    for opt in branch_select.find_elements(By.TAG_NAME, "option"):
        text = opt.text.strip()
        value = opt.get_attribute("value")
        if not text or "ընտրեք" in text.lower():
            continue  # skip placeholder
        dept_options.append((text, value))
    # Save the list in context if needed (for name lookup)
    # Note: This function might be called inside ConversationHandler where context is not directly accessible,
    # so ensure to store it in context.user_data in calling function if needed.
    return dept_options

def get_available_times(driver, date_str: str):
    """
    Helper function: For a given date (DD.MM.YYYY), select it in the UI and return a sorted list of available time slots (HH:MM).
    """
    # Convert date to YYYY-MM-DD format if needed for HTML date input
    try:
        day, month, year = date_str.split(".")
        html_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except ValueError:
        # If date_str is already in ISO format or another, use as is
        html_date = date_str
    # Find date input (assuming an <input type="date"> is present)
    date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
    if date_inputs:
        date_input = date_inputs[0]
        # Some date pickers might not allow direct send_keys; attempt to execute script
        try:
            driver.execute_script("arguments[0].value = arguments[1]", date_input, html_date)
            date_input.send_keys("\ue007")  # press Enter key (Unicode \ue007) to confirm
        except Exception:
            date_input.clear()
            date_input.send_keys(html_date)
            date_input.send_keys("\ue007")
    else:
        # If no date input found, the date might be selected via calendar widget or drop-downs.
        # In such case, try executing a script that sets the date by querying any date picker object.
        driver.execute_script("""
            var inputs = document.getElementsByTagName('input');
            for (var i=0; i<inputs.length; i++) {
                if (inputs[i].type==='text' && inputs[i].value.match(/\\d{4}-\\d{2}-\\d{2}/)) {
                    inputs[i].value = arguments[0];
                    if(typeof inputs[i].onchange === 'function'){ inputs[i].onchange(); }
                }
            }
        """, html_date)
    # Wait for times to load after date selection
    time.sleep(2)
    # Scrape the page for available times (look for patterns like "HH:MM")
    page_html = driver.page_source
    time_matches = re.findall(r"\d{1,2}:\d{2}", page_html)
    # Filter and sort unique times
    times = sorted({t for t in time_matches if re.match(r"^\d{1,2}:\d{2}$", t)})
    return times

def search_slots(driver, branch_value: str, exam_type: str, mode: str, search_value=None) -> str:
    """
    Select the given branch and exam type, then search for available slots according to the mode.
    mode = 'day' (find earliest available), 'date' (specific date in DD.MM.YYYY), or 'time' (next date with given HH:MM).
    search_value is used for 'date' (the date string) or 'time' (the time string).
    Returns a formatted result string in Armenian for the user.
    """
    result_text = ""
    # Select the desired branch in the dropdown
    try:
        select_elems = driver.find_elements(By.TAG_NAME, "select")
        branch_select_elem = None
        exam_select_elem = None
        # Identify branch and exam selects
        for sel in select_elems:
            opts = [opt.text for opt in sel.find_elements(By.TAG_NAME, "option")]
            if any("բաժին" in txt or "մարզ" in txt for txt in opts):
                branch_select_elem = sel
            elif any("քննություն" in txt or "քննական" in txt for txt in opts):
                exam_select_elem = sel
        # Fallback if not identified
        if branch_select_elem is None:
            branch_select_elem = select_elems[0]
            exam_select_elem = select_elems[1] if len(select_elems) > 1 else None
        # Select branch by value
        Select(branch_select_elem).select_by_value(branch_value)
        # Select exam type (theoretical/practical)
        if exam_select_elem:
            # If exam type is provided in options list
            if exam_type == "theoretical":
                # Look for option containing "Տեսական"
                for opt in exam_select_elem.find_elements(By.TAG_NAME, "option"):
                    if "տեսակ" in opt.text or "տեսական" in opt.text:
                        opt.click()
                        break
            elif exam_type == "practical":
                for opt in exam_select_elem.find_elements(By.TAG_NAME, "option"):
                    if "գործնական" in opt.text:
                        opt.click()
                        break
        else:
            # If exam type selection is not a dropdown (could be auto or not needed)
            pass
    except Exception as e:
        return "Տվյալների ընտրության ընթացքում սխալ տեղի ունեցավ։"
    # Perform search based on mode
    if mode == "day":
        # Find earliest available slot (iterate from today onwards)
        from datetime import datetime, timedelta
        today = datetime.today()
        found_date = None
        found_times = []
        for i in range(0, 60):  # check up to 60 days ahead
            d = today + timedelta(days=i)
            date_str = d.strftime("%d.%m.%Y")
            times = get_available_times(driver, date_str)
            if times:
                found_date = date_str
                found_times = times
                break
        if found_date:
            result_text = f"Առաջին հասանելի օրը՝ {found_date}, ազատ ժամեր՝ {', '.join(found_times)}"
        else:
            result_text = "Ներողություն, մոտակա օրերին ազատ քննության ժամեր չեն գտնվել։"
    elif mode == "date" and search_value:
        # Search for specific date
        date_str = search_value
        times = get_available_times(driver, date_str)
        if times:
            result_text = f"{date_str} օրỹ հասանելի ժամերն են՝ {', '.join(times)}"
        else:
            result_text = f"{date_str} օրվա համար ազատ ժամեր չկան։"
    elif mode == "time" and search_value:
        # Search for the next date that has the specified time available
        target_time = search_value
        from datetime import datetime, timedelta
        today = datetime.today()
        found_date = None
        for i in range(0, 60):
            d = today + timedelta(days=i)
            date_str = d.strftime("%d.%m.%Y")
            times = get_available_times(driver, date_str)
            if target_time in times:
                found_date = date_str
                break
        if found_date:
            result_text = f"Հաջորդ '{target_time}' ազատ քննությունը հասանելի է {found_date} օրը։"
        else:
            result_text = f"Հաջորդ {60} օրվա ընթացքում '{target_time}' ժամին ազատ քննության ժամանակ չի գտնվել։"
    else:
        result_text = "Սխալ որոնման ձև։"
    return result_text
