from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os, time
# If needed, import Select for dropdowns:
from selenium.webdriver.support.ui import Select
# For local use of ChromeDriverManager if no system Chrome available
from webdriver_manager.chrome import ChromeDriverManager

def fetch_available_slots(branch: str, exam_type: str):
    """Scrape the roadpolice.am site for available exam slots given a branch and exam type.
    Returns a list of slot time strings, or None if an error occurred."""
    # Configure Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Determine Chrome binary and driver paths (Render vs local)
    chrome_binary = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
    driver_path = "/opt/render/project/.render/chromedriver/chromedriver"
    if os.path.exists(chrome_binary):
        chrome_options.binary_location = chrome_binary
        service = Service(driver_path)
    else:
        # Fallback: use ChromeDriverManager to get a driver (for local testing)
        service = Service(ChromeDriverManager().install())
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Selenium driver error: {e}")
        return None

    slots = []
    try:
        driver.get("https://roadpolice.am/hy/hqb")
        # Allow page to load
        time.sleep(3)

        # Select the branch from dropdown (by visible text containing the branch name)
        try:
            branch_select = Select(driver.find_element(By.TAG_NAME, "select"))
            # The site likely has the first <select> for branches; adjust if necessary
            branch_select.select_by_visible_text(branch)
        except Exception:
            # Fallback: try to find option by text if direct select fails
            option_xpath = f"//option[contains(text(), '{branch}')]"
            option_elem = driver.find_element(By.XPATH, option_xpath)
            option_elem.click()

        # Select exam type. Assume the site shows a dropdown or radio for exam type.
        if exam_type in ["Տեսական քննություն", "Տեսական"]:
            exam_value = "Տեսական"
        else:
            exam_value = "Գործնական"
        try:
            exam_select = Select(driver.find_element(By.TAG_NAME, "select"))  # if there's a second <select>
            exam_select.select_by_visible_text(exam_value)
        except Exception:
            # If not a select element, try radio buttons or options
            exam_option_xpath = f"//*[contains(text(), '{exam_value}')]"
            exam_elem = driver.find_element(By.XPATH, exam_option_xpath)
            exam_elem.click()

        # If there's a search or submit button to load slots, click it (some forms require this).
        try:
            search_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Գրանցվել')]")
            search_btn.click()
        except Exception:
            pass  # perhaps selection auto-loads available slots

        # Wait for results to load (the site might dynamically load slots)
        time.sleep(5)  # a simple wait; ideally use WebDriverWait for a specific element

        # Scrape available slots.
        # We assume slots might be listed in elements containing date/time text. 
        # This is a placeholder logic and may need adjustments based on actual HTML structure.
        slot_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'slot') or contains(@class, 'time') or contains(text(), ':')]")
        # If no slot elements found, check for "no available" message
        if not slot_elements:
            # Look for an indicator of no availability (Armenian message or empty state)
            no_slot_texts = ["առկա չէ", "չկան", "暂无"]  # "no available" phrases in Armenian (and Chinese just in case)
            page_text = driver.page_source
            if any(txt in page_text for txt in no_slot_texts):
                slots = []  # explicitly no slots
            else:
                slots = []
        else:
            # Extract text from each slot element
            for elem in slot_elements:
                text = elem.text.strip()
                if text:
                    slots.append(text)
        # Optionally, sort slots chronologically if they are date strings
        # (Assuming dates are in a sortable format or can be parsed)
        # ... Sorting logic can be implemented here if needed ...
    except Exception as e:
        print(f"Error during scraping: {e}")
        slots = None
    finally:
        driver.quit()
    return slots
