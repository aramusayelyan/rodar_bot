import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# Render-installed binaries (from render-build.sh)
CHROME_BIN = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
CHROMEDRIVER_BIN = "/opt/render/project/.render/chromedriver/chromedriver"

def _build_driver():
    options = Options()
    # headless chrome flags
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")

    if os.path.exists(CHROME_BIN):
        options.binary_location = CHROME_BIN
        service = Service(CHROMEDRIVER_BIN)
        return webdriver.Chrome(service=service, options=options)
    else:
        # local fallback (Selenium Manager)
        return webdriver.Chrome(options=options)

def fetch_available_slots(branch_name: str, exam_type_label: str):
    """
    Վերադարձնում է ժամերի string-երի ցուցակ (կամ None, եթե սխալ է եղել)։
    Սխեմա․ բացում է https://roadpolice.am/hy/hqb, ընտրում է բաժինը և քննության տեսակը,
    ապա քերում հասանելի ժամերը։
    """
    driver = None
    try:
        driver = _build_driver()
        driver.set_page_load_timeout(60)
        driver.get("https://roadpolice.am/hy/hqb")
        time.sleep(3)

        page = driver.page_source
        # Ընտրում ենք բաժինը՝ option-ով, որը պարունակում է branch_name-ը
        try:
            opt = driver.find_element(By.XPATH, f"//option[contains(normalize-space(.), '{branch_name}')]")
            opt.click()
            time.sleep(1)
        except Exception:
            pass  # կանցնենք առանց սրա, եթե կայքի կառուցվածքը փոխված է

        # Ընտրում ենք քննության տեսակը (տեսական/գործնական)
        # Փորձում ենք գտնել համապատասխան option կամ radio/btn ըստ տեքստի
        exam_token = "տեսական" if "տեսական" in exam_type_label.lower() else "գործնական"
        try:
            exam_opt = driver.find_element(By.XPATH, f"//option[contains(translate(., 'ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔՕՖ', 'աբգդեզէըթժիլխծկհձղճմյունշոչպջրսվտրցւփքօֆ'), '{exam_token}')]")
            exam_opt.click()
            time.sleep(1)
        except Exception:
            try:
                exam_any = driver.find_element(By.XPATH, f"//*[contains(translate(., 'ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔՕՖ', 'աբգդեզէըթժիլխծկհձղճմյունշոչպջրսվտրցւփքօֆ'), '{exam_token}')]")
                exam_any.click()
                time.sleep(1)
            except Exception:
                pass

        # Հնարավոր է պետք լինի սեղմել "Գտնել/Գրանցվել" կոճակ
        try:
            btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Գրանց') or contains(text(),'Որոն')]")
            btn.click()
            time.sleep(3)
        except Exception:
            time.sleep(2)

        # Քերել հասանելի ժամերը (պահանջում է հարմարեցնել ըստ DOM-ի)
        # Պարզ հեուրիստիկա՝ վերցնենք բոլոր HH:MM նախշերը էջից
        html = driver.page_source
        times = sorted(set(re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", html)))
        slots = []

        # Փորձենք նաև վերցնել օր+ժամ օրինակային տողով
        # Եթե էջում կան տարրեր, որտեղ գրած են ժամերը, թույլ կտանք պահել ամբողջ տեքստը
        try:
            time_elems = driver.find_elements(By.XPATH, "//*[contains(text(), ':')]")
            for el in time_elems:
                txt = el.text.strip()
                if re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", txt):
                    # պահենք ամբողջ տողը, որպեսզի պարունակի նաև օրը/ամսաթիվը
                    slots.append(txt)
        except Exception:
            pass

        # Եթե slots դատարկ է, գոնե ժամը թողնենք
        if not slots and times:
            slots = times

        return slots
    except Exception:
        return None
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
