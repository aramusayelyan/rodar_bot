from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time

def fetch_availability():
    """
    Կանչում է roadpolice.am/hy/hqb էջը և քաղում բոլոր բաժինների (քաղաքների) և քննության երկու տիպերի 
    (տեսական/գործնական) համար ազատ օրերի և ժամերի տվյալները։
    Վերադարձնում է dictionary ձևաչափով տվյալները։
    """
    # Initialize headless Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")           # Աշխատել առանց GUI:contentReference[oaicite:6]{index=6}
    chrome_options.add_argument("--no-sandbox")        # Optional: Linux սերվերներում անհրաժեշտ է
    chrome_options.add_argument("--disable-dev-shm-usage")  # Optional: shared memory խնդիրների համար
    # Կարող ենք նշել browser-ի binary 위치, եթե default-ում չի գտնվում։
    #chrome_options.binary_location = "/usr/bin/google-chrome"  # uncomment if needed
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://roadpolice.am/hy/hqb")
    # Սպասել, որպեսզի էջի հիմնական մասը բեռնվի (ոչ պարտադիր explicit, բայց անվտանգ)
    driver.implicitly_wait(5)

    # Պահպանել արդյունքները
    availability = {}

    # Տարբերակ՝ պատրաստի branch option-ների ID-ներ:
    # Կամ կարող ենք վերցնել select-ից option-ների value-ները dynamic.
    # Ահա ենթադրաբար value-ները 1-13 համապատասխանում են վերևում նշված մեր branch_id-ներին։
    branch_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    # Համապատասխան branch-ի կարճ անունները (օրինակ, անգլերեն կամ լատին տառերով տարբերակով):
    branch_map = {
        1: "Yerevan", 2: "Gyumri", 3: "Vanadzor", 4: "Armavir",
        5: "Kotayk", 6: "Artashat", 7: "Ashtarak", 8: "Kapan",
        9: "Ijevan", 10: "Sevan", 11: "Martuni", 12: "Goris", 13: "Vayk"
    }

    # Գտնել էջի select տարրերը։
    # Ենթադրում ենք, որ առաջին select-ը վերաբերում է վարորդական վկայականի հերթագրման բաժնի ընտրությանը։
    select_elements = driver.find_elements(By.TAG_NAME, "select")
    if not select_elements:
        raise Exception("Branch select element not found on the page.")
    # Որոշում ենք, որ առաջին select-ը (index 0) մեր կարիքների select-ն է։
    branch_select_element = select_elements[0]
    branch_select = Select(branch_select_element)

    # Գտնել քննության տեսակի radio կոճակները։
    # Օգտվում ենք labels կամ value-ի հիման վրա։
    # Կանխավ վերցնենք երկու տարբեր radio input:
    theory_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Տեսական')]")
    practical_radio = driver.find_element(By.XPATH, "//label[contains(text(), 'Գործնական')]")

    for branch_id in branch_ids:
        # Ընտրել տվյալ branch-ը select-ից ըստ value
        try:
            branch_select.select_by_value(str(branch_id))
        except Exception as e:
            # Եթե value selection չի հաջողվում, փորձել ըստ visible text (նշենք որ տեքստը հայերեն է կայքում)
            # Ոչ միշտ հարմար, քանի որ select ունի երկար տեքստ։
            # Կարող ենք branch_select.select_by_index(branch_id) եթե value-ները համընկնում են։
            branch_select.select_by_index(branch_id - 1)
        # Ընտրել "Տեսական" radio
        theory_radio.click()
        # Սպասել, մինչև հասանելի ժամերի ցուցակը բեռնվի (կոնկրետ՝ option պարունակող ":" կցուցադրվի)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//option[contains(text(), ':')]"))
            )
        except Exception:
            pass  # եթե անգամ timeout է եղել, կփորձենք քաղել ինչ տվյալ կա

        # Քաղել տեսական քննության slots
        slots = driver.find_elements(By.XPATH, "//option[contains(text(), ':')]")
        theory_slots_by_date = {}
        for option in slots:
            text = option.text.strip()
            if not text:
                continue
            # text expected format: "DD.MM.YYYY HH:MM" կամ նման, կամ "YYYY-MM-DD HH:MM"
            # Բաժանել ημεաթիվ և ժամ
            # Ի տարբերություն, կգտնենք վերջին բացատով:
            sep_index = text.rfind(" ")
            if sep_index == -1:
                continue
            date_part = text[:sep_index]
            time_part = text[sep_index+1:]
            # Վերածել date_part-ը date օբյեկտի
            date_obj = None
            if "." in date_part:
                try:
                    date_obj = datetime.strptime(date_part, "%d.%m.%Y").date()
                except:
                    pass
            if date_obj is None and "-" in date_part:
                try:
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d").date()
                except:
                    pass
            if date_obj is None:
                # Չհաջողվեց parse անել ամսաթիվը
                continue
            # Ավելացնել list-ի մեջ
            if date_obj not in theory_slots_by_date:
                theory_slots_by_date[date_obj] = []
            theory_slots_by_date[date_obj].append(time_part)
        # Տեղաբաշխել availability dict-ի մեջ
        branch_name_key = branch_map.get(branch_id, str(branch_id))
        if branch_name_key not in availability:
            availability[branch_name_key] = {}
        availability[branch_name_key]["theory"] = {}
        # Ժամանակացույցերը դասավորել ըստ ամսաթվի (թվով key), և յուրաքանչյուրի time ցուցակը սորտավորել
        for date_obj, times in sorted(theory_slots_by_date.items()):
            times.sort(key=lambda t: datetime.strptime(t, "%H:%M").time())
            availability[branch_name_key]["theory"][date_obj] = times

        # Հիմա գործնական քննության համար։
        # Սեղմել "Գործնական" radio և սպասել slots-ի փոփոխման։
        # Կարող է արդեն տեսական slots-երը բեռնված են, պետք է սպասել նորերի բեռնումը։
        old_options_texts = {opt.text for opt in slots}
        practical_radio.click()
        try:
            WebDriverWait(driver, 7).until(lambda drv: 
                {opt.text for opt in drv.find_elements(By.XPATH, "//option[contains(text(), ':')]")} != old_options_texts
            )
        except Exception:
            # Չսպասել ավելի, անցնել առաջ
            pass

        # Քաղել գործնական slots
        slots = driver.find_elements(By.XPATH, "//option[contains(text(), ':')]")
        practical_slots_by_date = {}
        for option in slots:
            text = option.text.strip()
            if not text:
                continue
            sep_index = text.rfind(" ")
            if sep_index == -1:
                continue
            date_part = text[:sep_index]
            time_part = text[sep_index+1:]
            date_obj = None
            if "." in date_part:
                try:
                    date_obj = datetime.strptime(date_part, "%d.%m.%Y").date()
                except:
                    pass
            if date_obj is None and "-" in date_part:
                try:
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d").date()
                except:
                    pass
            if date_obj is None:
                continue
            if date_obj not in practical_slots_by_date:
                practical_slots_by_date[date_obj] = []
            practical_slots_by_date[date_obj].append(time_part)
        # Ավելացնել availability dict-ին
        availability.setdefault(branch_name_key, {})
        availability[branch_name_key]["practical"] = {}
        for date_obj, times in sorted(practical_slots_by_date.items()):
            times.sort(key=lambda t: datetime.strptime(t, "%H:%M").time())
            availability[branch_name_key]["practical"][date_obj] = times

        # Նկատել՝ այստեղ մենք էջը նորից չենք բեռնում յուրաքանչյուր branch-ի համար։
        # Մենք օգտագործում ենք նույն page-ը՝ փոփոխելով select արժեքը։
        # Որոշ դեպքերում հնարավոր է պետք լինի փոքր դադար տալ միջևը։
        time.sleep(1)  # փոքր հապաղում հաջորդ iteration-ից առաջ։
    
    # Ավարտել:
    driver.quit()
    return availability
