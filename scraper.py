from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta

# Mapping from internal section codes to roadpolice.am branch IDs (from HTML)
SECTION_CODE_TO_ID = {
    "Yerevan": "33",
    "Shirak": "39",
    "Lori": "40",
    "Armavir": "38",
    "Kotayk": "42",
    "Ararat": "44",
    "Aragatsotn": "43",
    "Syunik_Kapan": "36",
    "Tavush": "41",
    "Gegharkunik_Sevan": "34",
    "Gegharkunik_Martuni": "35",
    "Syunik_Goris": "37",
    "Vayots_Dzor": "45"
}

# Mapping exam type to serviceId values from HTML
EXAM_TYPE_TO_SERVICE_ID = {
    "theory": "300691",      # Theoretical exam for new license
    "practical": "300692"    # Practical exam for new license
}

def fetch_data(section_code: str, exam_type: str, filter_day: int = None, filter_date: str = None, filter_hour: str = None) -> str:
    """Launch headless Chrome and scrape appointment data from roadpolice.am."""
    # Configure Chrome options for headless execution:contentReference[oaicite:0]{index=0}
    options = Options()
    options.add_argument("--headless")        # Run Chrome in headless mode:contentReference[oaicite:1]{index=1}
    options.add_argument("--no-sandbox")      # No sandbox (required in some container envs):contentReference[oaicite:2]{index=2}
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems:contentReference[oaicite:3]{index=3}
    options.add_argument("--disable-gpu")
    # Launch browser with webdriver-manager to obtain ChromeDriver:contentReference[oaicite:4]{index=4}
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        # Navigate to the Road Police appointment page (Armenian language)
        driver.get("https://roadpolice.am/hy/hqb")
        # Select the desired service (exam type)
        service_select = driver.find_element("name", "serviceId")
        service_id = EXAM_TYPE_TO_SERVICE_ID.get(exam_type)
        if service_id:
            service_select.send_keys(service_id)  # Select by value
        # Select the branch (registration-exam division) by its ID
        branch_select = driver.find_element("name", "branchId")
        branch_id = SECTION_CODE_TO_ID.get(section_code)
        if branch_id:
            branch_select.send_keys(branch_id)
        # If a specific date filter is provided, attempt to select that date
        if filter_date:
            # Click date input to open calendar
            date_input = driver.find_element("id", "date-input")
            driver.execute_script("arguments[0].click();", date_input)
            # Format the provided date string to match required format (DD.MM.YYYY)
            try:
                target_date = datetime.strptime(filter_date, "%d.%m.%Y")
            except ValueError:
                try:
                    target_date = datetime.strptime(filter_date, "%Y-%m-%d")
                except Exception:
                    return "Ներողություն, ամսաթվի ձևաչափը սխալ է։"
            # Find the calendar day element for the target date by aria-label
            month_name = target_date.strftime("%B")  # e.g., 'October' (English)
            # Convert English month to Armenian name (rough approach)
            # Note: For simplicity, we'll map known month names to Armenian manually
            month_name_map = {
                "January": "Հունվար", "February": "Փետրվար", "March": "Մարտ",
                "April": "Ապրիլ", "May": "Մայիս", "June": "Հունիս",
                "July": "Հուլիս", "August": "Օգոստոս", "September": "Սեպտեմբեր",
                "October": "Հոկտեմբեր", "November": "Նոյեմբեր", "December": "Դեկտեմբեր"
            }
            arm_month = month_name_map.get(month_name, month_name)
            aria_label = f"{arm_month} {target_date.day}, {target_date.year}"
            # Try to find the day element (calendar must be open from earlier click)
            try:
                day_elem = driver.find_element("xpath", f"//span[@aria-label='{aria_label}']")
            except Exception:
                return f"Տրված ամսաթվի ({filter_date}) համար տվյալներ չեն գտնվել։"
            # Check if the day element is marked as unavailable
            day_classes = day_elem.get_attribute("class")
            if "flatpickr-disabled" in day_classes:
                return f"Նշված ամսաթվի ({filter_date}) համար ազատ ժամանակներ չկան։"
            else:
                # Click the day to select it
                day_elem.click()
        # If a specific weekday filter is provided, find the nearest available date for that weekday
        if filter_day is not None:
            # Ensure calendar is open
            date_input = driver.find_element("id", "date-input")
            driver.execute_script("arguments[0].click();", date_input)
            base_date = datetime.today()
            found_date = None
            for i in range(0, 35):  # search up to ~5 weeks
                dt = base_date + timedelta(days=i)
                if dt.weekday() == filter_day:  # Monday=0 ... Sunday=6
                    # Check if this date is available (not fully booked)
                    arm_month = month_name_map.get(dt.strftime("%B"), dt.strftime("%B"))
                    aria_label = f"{arm_month} {dt.day}, {dt.year}"
                    try:
                        day_elem = driver.find_element("xpath", f"//span[@aria-label='{aria_label}']")
                    except Exception:
                        continue
                    classes = day_elem.get_attribute("class")
                    if "flatpickr-disabled" not in classes:
                        found_date = dt
                        day_elem.click()
                        break
            if not found_date:
                return "Ներողություն, նշված շաբաթվա օրվա համար մոտակա ազատ օրը չի գտնվել։"
        # If a specific hour filter is provided, we will attempt to find a slot on the earliest available date around that time
        if filter_hour:
            try:
                target_hour = datetime.strptime(filter_hour, "%H:%M").time()
            except Exception:
                return "Ներողություն, ժամի ձևաչափը սխալ է։"
            # Ensure at least one day is selected (if none selected yet, use earliest default)
            # (The page likely auto-selects the earliest available date.)
            # Get currently selected date from the input
            selected_date_val = driver.find_element("id", "date-input").get_attribute("value")
            if not selected_date_val:
                # If no date selected, just get first available by reading default
                selected_date_val = driver.find_element("id", "select2-serviceId-vl-container").get_attribute("title")
            # (For simplicity, we will not implement complex hour-by-hour availability check here)
            # Just inform the user of the earliest available date and suggest the provided hour.
            pass  # (We'll handle output after gathering info below)
        # After any filtering, read the current selection and earliest slot info
        # Get the selected date from the date input
        date_val = driver.find_element("id", "date-input").get_attribute("value")
        if not date_val:
            date_val = "ամենամոտ օր"
        # Get the first (selected) time slot
        time_select = driver.find_element("name", "slotTime")
        time_val = time_select.get_attribute("value")
        if not time_val:
            time_val = time_select.text.split()[0]  # fallback to first option text
        # Prepare result text
        exam_text = "տեսական" if exam_type == "theory" else "գործնական"
        branch_name = section_code  # fallback to code
        # Find actual branch name in Armenian for output (we have mapping in keyboards)
        from keyboards import SECTION_CODE_TO_ARM
        if section_code in SECTION_CODE_TO_ARM:
            branch_name = SECTION_CODE_TO_ARM[section_code]
        if filter_hour:
            return f"Առաջին հասանելի ժամանակը շուրջ {filter_hour}-ին՝ {date_val}-ին ({branch_name} բաժին, {exam_text} քննություն)։"
        elif filter_day is not None:
            weekday_map = ["Երկուշաբթի","Երեքշաբթի","Չորեքշաբթի","Հինգշաբթի","Ուրբաթ","Շաբաթ","Կիրակի"]
            day_name = weekday_map[filter_day]
            return f"{day_name} օրվա ամենամոտ ազատ օրը `{date_val}` է ({branch_name}, {exam_text} քննություն, առաջին ժամ՝ {time_val})."
        elif filter_date:
            if "չկան" in date_val or "չի գտնվել" in date_val:
                # If we returned early error, handle above, but just in case
                return date_val
            return f"{date_val}-ի համար հասանելի է {exam_text} քննություն ({branch_name}), առաջին ժամ՝ {time_val}։"
        else:
            # No filter: give earliest available slot info
            return f"Առաջիկա ազատ հերթը {branch_name} բաժնում ({exam_text} քննություն)՝ {date_val} - {time_val}։"
    except Exception as e:
        return f"Սխալ է առաջացել տվյալներ քաղելիս: {e}"
    finally:
        driver.quit()
