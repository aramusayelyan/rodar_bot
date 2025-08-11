from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

# Selenium-ով page բեռնելու և տվյալներ քաղելու հիմնական ֆունկցիա
def get_free_slots(branch_name: str, exam_type: str):
    """
    Ընդունում է բաժանմունքի անունը և քննության տեսակը,
    վերադարձնում է տվյալ բաժանմունքում տվյալ ծառայության համար առկա առաջին մի քանի ազատ օրերի և ժամերի ցանկը։
    Եթե ազատ օրեր չկան, վերադարձնում է դատարկ ցանկ։
    """
    # 1. Կոնֆիգուրացնել headless Chrome-ի options-ները
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Նորացված headless ռեժիմ Chrome 109+ համար
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # Ընդհանուր user-agent, թե անհրաժեշտ չէ: Կարող ենք չսահմանել, թողնել default

    # 2. Browser-ի driver-ը ստանալ (Selenium 4+ ավտոմատ կբեռնի chromedriver-ը, եթե Chrome-ը PATH-ում է)
    driver = webdriver.Chrome(options=chrome_options)
    try:
        # 3. Բացել roadpolice.am կայքի հաշվի և քննության հերթագրման էջը (հայերեն տարբերակը)
        driver.get("https://roadpolice.am/hy/hqb")

        # Սպասել, որ էջը բեռնվի և համապատասխան տարրերը լինեն մատչելի
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//body"))
        )
        # Եթե անհրաժեշտ լիներ, կարող ենք սպասել կոնկրետ input դաշտի հայտնվելուն

        # 4. Լրացնել ձևը:
        # ա) Ընտրել "քննության/գործողության տեսակը"՝ ըստ exam_type:
        # Կայքում այս ընտրությունը արտադրված է radio button-ներով։
        # exam_type ստացվում է բոտի կողմից հետևյալ հնարավորություններով.
        # "Տեսական քննություն", "Գործնական քննություն", "Վար. վկայականի Փոխարինում", "Վար. վկայականի Կորուստ"
        # Դրանք համապատասխանեցնենք կայքի radio-ների տեքստերին.
        if "Տեսական" in exam_type:
            # գտնել "Տեսական" radio input-ը և սեղմել
            theo_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Տեսական')]/input")
            driver.execute_script("arguments[0].click();", theo_radio)
        elif "Գործնական" in exam_type:
            prac_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Գործնական')]/input")
            driver.execute_script("arguments[0].click();", prac_radio)
        elif "Փոխարինում" in exam_type:
            exch_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Փոխարինում')]/input")
            driver.execute_script("arguments[0].click();", exch_radio)
        elif "Կորուստ" in exam_type:
            loss_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Կորուստ')]/input")
            driver.execute_script("arguments[0].click();", loss_radio)

        # բ) Ընտրել ստորաբաժանումը dropdown-ից ըստ branch_name:
        # Կայքի HTML-ում բաժանմունքի ընտրումը հնարավոր է select -> option էլեմենտով։
        # Մենք կփորձենք ընտրել option-ի ըստ տեքստի համապատասխանեցմամբ։
        from selenium.webdriver.support.select import Select
        select_element = Select(driver.find_element(By.XPATH, "//select"))
        # Վերոնշյալ find_element("//select") ենթադրում է, որ էջում առաջին select-ը հենց վարորդական բաժնի ընտրությունն է։
        # (Այլընտրանք: find_element(By.XPATH, "//select[option[contains(text(), 'բաժանմունք')]]") )
        select_element.select_by_visible_text(branch_name)

        # գ) Այժմ պետք է աշխատել "Այցի օրը և ժամը" դաշտի հետ։
        # Կայքը օգտագործում է օրացույց-ժամ ընտրիչ։ Փորձենք բացել օրացույցը և գտնել հասանելի օրերը։
        date_input = driver.find_element(By.XPATH, "//input[@type='date' or @name='visitDate' or @name='date']")
        # Որոշում. եթե input-ը type='date' է, որոշ բրաուզերներում (headless) custom widget չկիրառվի։
        # Սակայն կայքը հաարաբար JavaScript-ով է կցում widget։
        # Ամեն դեպքում, փորձենք սեղմել, որպեսզի օրացույցը երևա.
        date_input.click()

        # դ) Փնտրել օրացույցում enabled (հասանելի) օրերը։
        available_dates = []
        months_checked = 0
        # պարզ regex pattern ամսաթվի համար
        date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
        while len(available_dates) < 3 and months_checked < 12:
            # գտնել օրացույցում այն օրերը, որոնք ունենք enabled (առանց disabled class-ի)
            days = driver.find_elements(By.XPATH, "//span[contains(@class, 'day') and not(contains(@class, 'disabled')) and not(contains(@class, 'prev')) and not(contains(@class, 'next'))]")
            # Վերացված class-երի միջոցով փորձում ենք առանձնացնել тек current month-ի օրերը, որոնք ակտիվ են։
            for day_elem in days:
                aria_label = day_elem.get_attribute("aria-label")  # օրինակ "Friday, March 15, 2025"
                date_value = None
                if aria_label:
                    # Փորձենք aria-label-ից հանել ամսաթիվը YYYY-MM-DD ձևաչափով։
                    # Flatpickr-ի դեպքում aria-label կարող է լինել "2025-03-15" կամ բառերով։
                    match = date_pattern.search(aria_label)
                    if match:
                        date_value = match.group(0)
                if not date_value:
                    # Եթե aria-label չկար կամ չէր պարունակում, փորձենք data-date ատրիբուտը։
                    date_value = day_elem.get_attribute("data-date") or day_elem.get_attribute("date")
                if not date_value:
                    # Վերջին տարբերակ՝ վերցնենք тек current տեսանելի ամսվա և տարվա վերնագրից և օրվա համարից։
                    # Ստանալ тек current ամսվա անվանումը և տարին:
                    try:
                        month_year_text = driver.find_element(By.XPATH, "//div[contains(@class, 'month')]").text
                        # ожидается ֆորմատ, բայց եթե չի ստացվում, թողնենք։
                        month_year = month_year_text
                    except:
                        month_year = ""
                    day_number = day_elem.text.strip()
                    date_value = f"{month_year} {day_number}"
                # Ավելացնել գտնված ամսաթիվը արդյունքների մեջ
                if date_value:
                    available_dates.append(date_value)
                    if len(available_dates) >= 3:
                        break
            if len(available_dates) >= 3 or months_checked >= 11:
                break
            # եթե բավարար օրեր չգտանք այս ամսում, անցնել հաջորդ ամսվա
            try:
                next_btn = driver.find_element(By.XPATH, "//span[@class='flatpickr-next-month' or contains(@class, 'next')]")
                next_btn.click()
            except Exception as e:
                break  # չեն գտել հաջորդ ամիս кнопка, կամ սխալ՝ դուրս գալ ցիկլից
            months_checked += 1
            WebDriverWait(driver, 5).until(EC.staleness_of(days[0]) if days else True)  # սպասել, որ նոր ամսվա օրերը բեռնվեն

        # ե) Այս պահին available_dates ցուցակում ունենք մինչև 3 մոտակա ազատ ամսաթվի տեքստ (format: YYYY-MM-DD կամ այլ)։
        free_slots = []  # այստեղ կհավաքենք (ամսաթիվ, ժամեր) զույգեր
        for date_val in available_dates:
            # Պտույտ ամեն մի ամսաթվի համար՝ refresh անենք էջը և query 해당 date-ի ժամերը։
            driver.refresh()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            # Կրկին սահմանել նախորդ ընտրությունները (քանի որ refresh-ից հետո data կզրոյանա)
            if "Տեսական" in exam_type:
                theo_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Տեսական')]/input")
                driver.execute_script("arguments[0].click();", theo_radio)
            elif "Գործնական" in exam_type:
                prac_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Գործնական')]/input")
                driver.execute_script("arguments[0].click();", prac_radio)
            elif "Փոխարինում" in exam_type:
                exch_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Փոխարինում')]/input")
                driver.execute_script("arguments[0].click();", exch_radio)
            elif "Կորուստ" in exam_type:
                loss_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Կորուստ')]/input")
                driver.execute_script("arguments[0].click();", loss_radio)
            select_element = Select(driver.find_element(By.XPATH, "//select"))
            select_element.select_by_visible_text(branch_name)
            date_input = driver.find_element(By.XPATH, "//input[@type='date' or @name='visitDate' or @name='date']")
            # Input դաշտը լրացնել համապատասխան ամսաթվով։
            try:
                date_input.send_keys(date_val)
            except Exception:
                # Եթե type=date է, send_keys-ի ձևաչափը պետք է լինի YYYY-MM-DD
                # համոզվենք, որ հենց այդպես է date_val-ը, եթե ոչ՝ ձևափոխենք:
                if re.match(r'\d{4}-\d{2}-\d{2}', date_val):
                    date_str = date_val
                else:
                    # Փորձենք date_val-ը parse անել ամսաթիվ։
                    # (Այստեղ կարող ենք օգտագործել datetime.strptime եթե ձևաչափը հայտնի լինի։
                    date_str = date_val  #fallback
                date_input.send_keys(date_str)
            # Որոշ դեպքերում հնարավոր է date_input.send_keys-ը չտեղադրի արժեքը եթե date picker-ը custom է:
            # Այն դեպքում կփորձենք JavaScript-ով value-դնել.
            if date_input.get_attribute("value") == "" and re.match(r'\d{4}-\d{2}-\d{2}', date_val):
                driver.execute_script(f"arguments[0].value = '{date_val}';", date_input)
            # Այժմ սպասել, որ տվյալ օրվա համար ժամերի ցանկը բեռնվի։
            # Հնարավոր է, որ ժամերը էջում հայտնվեն որպես radio button-ների լիստ կամ dropdown։
            # Փորձենք սպասել որևէ հայտնի timeslot-ի presence-ին։
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), ':')]"))
            )
            # հավաքել ժամերի տարբերակները
            slot_times = []
            # Hնարավոր սխեմաներ՝ կամ <option> թեգերով են ժամերը, կամ <label>-ով radio:
            time_options = driver.find_elements(By.XPATH, "//option[contains(text(), ':')]")
            if not time_options:
                time_options = driver.find_elements(By.XPATH, "//label[contains(text(), ':')]")
            for opt in time_options:
                text = opt.text
                # Ֆիլտրել համոզվելու համար, որ իրական ժամը պատկերող տող է (օր. "11:00" ձևաչափով)
                if ":" in text:
                    slot_times.append(text.strip())
            free_slots.append((date_val, slot_times))
        return free_slots

    finally:
        driver.quit()
