from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

def get_free_dates(branch_id=None, exam_type=None):
    """Վերադարձնում է ազատ օրերի և ժամերի ցանկը"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://roadpolice.am/hy/hqb")
    time.sleep(2)

    # Այստեղ ավելացրու branch_id, exam_type filter-ները
    # Օրինակ՝ branch selector
    # driver.find_element(By.CSS_SELECTOR, f"option[value='{branch_id}']").click()

    results = []

    try:
        # Սա օրինակ է, selector-ները պետք է հարմարեցնել ըստ կայքի կառուցվածքի
        days = driver.find_elements(By.CSS_SELECTOR, ".day-class")
        for day in days:
            date_text = day.text
            results.append(date_text)
    except:
        pass

    driver.quit()
    return results
