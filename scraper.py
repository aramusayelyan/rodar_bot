import logging
from datetime import datetime

# Սիմուլյացիայի համար պահվող գրանցումների OTP կոդերը (բազմակի գրանցման գործընթացների համար)
_pending_registrations = {}

def start_registration(phone_number, social_card):
    """
    Simulate initiating the registration on the government exam site.
    Sends an SMS code to the user's phone (simulated by generating a code).
    """
    # Generate a 4-digit confirmation code (simulation)
    code = str(1000 + __import__("random").randint(0, 8999))
    # Store the code in pending dict
    _pending_registrations[phone_number] = code
    # Log the event (in real scenario, an SMS would be sent to user)
    logging.info(f"Simulated registration: sent OTP code {code} to phone {phone_number}")
    # Return success status
    return True

def complete_registration(phone_number, code_entered):
    """
    Simulate completing the registration by verifying the SMS code.
    In this simulation, any numeric code is accepted. If incorrect, it logs a warning.
    """
    real_code = _pending_registrations.get(phone_number)
    if real_code is None:
        # No pending registration found for this phone (unexpected in normal flow)
        logging.warning(f"No pending registration for phone {phone_number}")
        return False
    if code_entered != real_code:
        # OTP is incorrect, but for demo purposes we will proceed anyway
        logging.warning(f"Entered OTP {code_entered} does not match real OTP {real_code} (proceeding in demo mode).")
    else:
        logging.info(f"OTP {code_entered} verified successfully for phone {phone_number}.")
    # Registration completed (simulate finalizing on external site)
    _pending_registrations.pop(phone_number, None)  # remove pending entry
    return True

def get_available_slots(exam_type, branch, filter_type=None, filter_value=None):
    """
    Fetch available exam slots (simulated data or real via scraping).
    If filter_type is provided, filter the slots accordingly.
    """
    # Քանի որ իրական կայքի API-ն կամ տվյալները անմիջապես հասանելի չեն,
    # այստեղ օգտագործվում է սիմուլյացված ժամանակացույց:
    # Օրինակ՝ Selenium-ի կիրառման համար (եթե իրական scraping իրականացվեր), կոդը կերևար այսպես.
    #
    # from selenium import webdriver
    # options = webdriver.ChromeOptions()
    # options.headless = True
    # driver = webdriver.Chrome(options=options)
    # try:
    #     driver.get("<booking_site_url>")
    #     # Այստեղ կկատարվեին գործողություններ՝ ընտրելու exam_type և branch համապատասխան drop-down մենյուներից,
    #     # այնուհետեւ կվերծանվեին ազատ ժամերը:
    #     # ... (scraping logic) ...
    # finally:
    #     driver.quit()
    #
    # Ստացված տվյալները պէտք է մշակվեն և վերադարձվեն։
    #
    # Այժմ՝ սիմուլյացված տվյալներ.
    slots = [
        ("15.09.2025", "09:16"),
        ("15.09.2025", "10:00"),
        ("16.09.2025", "14:00"),
        ("17.09.2025", "11:24"),
        ("18.09.2025", "09:16"),
        ("19.09.2025", "09:16"),
        ("20.09.2025", "09:16")
    ]
    # Ֆիլտրել ըստ exam_type կամ branch, եթե անհրաժեշտ է։
    # (Սիմուլյացիայում exam_type և branch չեն ազդում արդյունքների վրա)
    filtered_slots = slots

    # Apply filter by type
    if filter_type == "hour":
        # Filter slots by hour (two-digit hour)
        target_hour = filter_value.zfill(2)  # ensure two-digit string
        filtered_slots = [s for s in filtered_slots if s[1].startswith(target_hour)]
    elif filter_type == "date":
        filtered_slots = [s for s in filtered_slots if s[0] == filter_value]
    elif filter_type == "weekday":
        # Convert Armenian weekday name to weekday number (0=Monday,6=Sunday)
        weekdays_map = {
            "Երկուշաբթի": 0, "Երեքշաբթի": 1, "Չորեքշաբթի": 2,
            "Հինգշաբթի": 3, "Ուրբաթ": 4, "Շաբաթ": 5, "Կիրակի": 6
        }
        try:
            weekday_num = weekdays_map[filter_value.capitalize()]
        except KeyError:
            weekday_num = None
        if weekday_num is not None:
            filtered_slots = [
                s for s in filtered_slots 
                if datetime.strptime(s[0], "%d.%m.%Y").weekday() == weekday_num
            ]
        else:
            filtered_slots = []  # if invalid weekday (shouldn't happen due to prior validation)
    # Return filtered list of (date, time) tuples
    return filtered_slots
