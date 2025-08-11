from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time

def fetch_availability():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://roadpolice.am/hy/hqb")
    driver.implicitly_wait(5)

    availability = {}

    branch_select = Select(driver.find_element(By.TAG_NAME, "select"))
    theory_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Տեսական')]")
    practical_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Գործնական')]")

    branch_map = {
        option.get_attribute("value"): option.text 
        for option in branch_select.options
    }

    for value, name in branch_map.items():
        branch_select.select_by_value(value)
        # Process both exam types
        for exam_type, radio in [("Տեսական", theory_radio), ("Գործնական", practical_radio)]:
            radio.click()
            WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.XPATH, "//option[contains(text(), ':')]"))
            )
            options = driver.find_elements(By.XPATH, "//option[contains(text(), ':')]")
            slots = {}
            for opt in options:
                txt = opt.text.strip()
                if not txt:
                    continue
                sep = txt.rfind(" ")
                dt = txt[:sep]
                tm = txt[sep + 1:]
                try:
                    d_obj = datetime.strptime(dt, "%d.%m.%Y").date()
                except ValueError:
                    continue
                slots.setdefault(d_obj, []).append(tm)
            # Sort times
            for k in slots:
                slots[k].sort()
            availability.setdefault(name, {})[exam_type] = slots
        time.sleep(1)

    driver.quit()
    return availability
