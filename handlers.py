from telegram import ReplyKeyboardRemove
import re
import logging

# Import other modules
import db
import scraper
import keyboards

# Define conversation state constants
# States for registration (/start)
STATE_PHONE, STATE_SOCIAL, STATE_CODE = range(3)
# States for slot search (/search)
STATE_EXAM, STATE_BRANCH, STATE_FILTER, STATE_HOUR, STATE_DATE, STATE_WEEKDAY = range(3, 3+6)

# Start command handler for registration flow
async def start_command(update, context):
    """Handle /start command. Asks for phone number and initiates registration."""
    user_id = update.effective_user.id
    # Ստուգել, արդյոք օգտատերը արդեն գրանցված է
    user = db.get_user_by_telegram_id(user_id)
    if user:
        # Եթե արդեն գոյություն ունի, ավարտել զրույցը և տեղեկացնել օգտատիրոջը
        await update.message.reply_text(
            "Դուք արդեն գրանցված եք։ Կարող եք օգտագործել /search՝ քննության ժամեր որոնելու համար։"
        )
        return ConversationHandler.END

    # Ողջույնի հաղորդագրություն և հեռախոսահամարի հարցում
    await update.message.reply_text(
        "Բարի գալուստ։\nԽնդրում ենք կիսվել Ձեր հեռախոսահամարով՝ սեղմելով ստորև բերված կոճակը։",
        reply_markup=keyboards.phone_request_keyboard
    )
    return STATE_PHONE

# Handler for receiving phone number (Telegram contact or text)
async def handle_contact(update, context):
    """Processes the user's phone number (contact or manual input)."""
    message = update.message
    phone_number = None

    if message.contact:
        # Օգտատերը կիսվել է իր կոնտակտով
        phone_number = message.contact.phone_number
    elif message.text:
        # Օգտատերը մուտքագրել է հեռախոսի համարը ձեռքով
        # Leave only digits (remove spaces, dashes, etc.)
        raw = re.sub(r"\D", "", message.text)
        if len(raw) < 8:  # շատ կարճ համար
            await message.reply_text("Խնդրում ենք մուտքագրել գործող հեռախոսահամար կամ կիսվել կոնտակտով։")
            return STATE_PHONE
        # Normalize Armenian phone format (if starts with 0 and 9 digits, assume Armenian mobile)
        if raw.startswith("0") and len(raw) == 9:
            raw = "+374" + raw[1:]
        elif raw.startswith("374") and not raw.startswith("+"):
            raw = "+" + raw
        elif not raw.startswith("+"):
            # If not starting with +, add + assuming it might be international already without plus
            raw = "+" + raw
        phone_number = raw

    # Եթե հեռախոսահամարը ստացվել է
    if phone_number:
        context.user_data["phone"] = phone_number
        # Հարցնել սոցիալական քարտի համարը (ՀԾՀ)
        await message.reply_text("Հիմա մուտքագրեք Ձեր հանրային ծառայության համարանիշը (ՀԾՀ):", 
                                  reply_markup=ReplyKeyboardRemove())
        return STATE_SOCIAL

    # Եթե որևէ պատճառով համար չի ստացվել, կրկին հարցնել
    await message.reply_text("Խնդրում ենք ուղարկել Ձեր հեռախոսահամարը ճիշտ ձևաչափով կամ օգտագործել կոնտակտի կոճակը։")
    return STATE_PHONE

# Handler for receiving social card number (ՀԾՀ)
async def handle_social(update, context):
    """Processes the user's social card number (ՀԾՀ)."""
    social_input = update.message.text
    # Թույլ տալ միայն թվանշաններ
    social_digits = re.sub(r"\D", "", social_input)
    if len(social_digits) != 10:
        # ՀԾՀ որպես կանոն բաղկացած է 10 թվանշանից
        await update.message.reply_text("ՀԾՀ phải կազմված լինի 10 թվանշանից, խնդրում ենք փորձել կրկին։")
        return STATE_SOCIAL

    context.user_data["social"] = social_digits
    phone = context.user_data.get("phone")
    social = social_digits

    # Փորձել գրանցվել կառավարական կայքում (սիմուլացված)
    success = scraper.start_registration(phone, social)
    if not success:
        # Եթե գրանցումը ձախողվել է (սիմուլյացված), ավարտել զրույցը սխալի հաղորդագրությամբ
        await update.message.reply_text("Ցավոք, գրանցվել չի ստացվել։ Խնդրում ենք փորձել կրկին ավելի ուշ։",
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Եթե հաջող, կայքը ուղարկել է SMS կոդ (սիմուլացված)
    await update.message.reply_text(
        "Ձեր հեռախոսահամարին ուղարկվել է SMS հաստատման կոդ։ Խնդրում ենք մուտքագրել ստացված կոդը։"
    )
    return STATE_CODE

# Handler for receiving SMS code
async def handle_code(update, context):
    """Processes the SMS verification code input by the user."""
    code_input = update.message.text.strip()
    # Ստուգել, որ կոդը բաղկացած է միայն թվերից
    if not code_input.isdigit():
        await update.message.reply_text("Կոդը պետք է պարունակի միայն թվանշաններ։ Խնդրում ենք փորձել կրկին։")
        return STATE_CODE

    phone = context.user_data.get("phone")
    social = context.user_data.get("social")
    # Verify the code (simulation: any numeric code is accepted)
    verified = scraper.complete_registration(phone, code_input)
    if not verified:
        # (Այս բլոկը սովորաբար կաշխատի, եթե կոդը սխալ է. Սիմուլացիայում սա չի կիրառվի)
        await update.message.reply_text("Սխալ կոդ։ Խնդրում ենք փորձել կրկին։")
        return STATE_CODE

    # Գրանցումը հաստատված է, պահել օգտատիրոջ տվյալները տվյալների բազայում
    new_user_id = db.add_user(update.effective_user.id, phone, social)
    context.user_data["user_id"] = new_user_id  # պահել user_id հետագա օգտագործման համար

    await update.message.reply_text(
        "Գրանցումն ավարտվեց հաջողությամբ։ Այժմ կարող եք օգտագործել /search հրամանը՝ քննության ազատ ժամեր փնտրելու համար։",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# Search command handler (entry point for searching exam slots)
async def search_command(update, context):
    """Handle /search command. Initiates the exam slot search flow."""
    user_id = update.effective_user.id
    # Ստուգել՝ օգտատերը գրանցված է թե ոչ
    user = db.get_user_by_telegram_id(user_id)
    if not user:
        await update.message.reply_text("Դուք դեռ գրանցված չեք: Խնդրում ենք նախ օգտագործել /start հրամանը գրանցման համար։")
        return ConversationHandler.END

    # Պահպանել user_id կոնտեքստում (օգտագործողի նախընտրությունները պահպանելու համար)
    context.user_data["user_id"] = user["id"]
    # Հարցնել քննության տեսակը (տեսական կամ գործնական)
    await update.message.reply_text(
        "Ընտրեք քննության տեսակը՝",
        reply_markup=keyboards.exam_type_keyboard
    )
    return STATE_EXAM

# Handler for exam type selection
async def handle_exam_type(update, context):
    """Processes the chosen exam type (theoretical or practical)."""
    text = update.message.text.strip().lower()
    exam_type = None
    if "տեսական" in text:
        exam_type = "Տեսական"
    elif "գործնական" in text:
        exam_type = "Գործնական"
    else:
        # Անհայտ արժեք, կրկին հարցնել
        await update.message.reply_text("Խնդրում ենք ընտրել քննության տեսակը՝ «Տեսական» կամ «Գործնական» ցուցակից։")
        return STATE_EXAM

    context.user_data["exam_type"] = exam_type
    # Հարցնել հաշվառման-քննական բաժինը
    await update.message.reply_text(
        "Ընտրեք հաշվառման-քննական բաժինը՝",
        reply_markup=keyboards.branch_keyboard
    )
    return STATE_BRANCH

# Handler for branch selection
async def handle_branch(update, context):
    """Processes the selected DMV branch for exam."""
    branch_text = update.message.text.strip()
    # Ստուգել, որ մուտքագրված արժեքը մեր ցանկից է
    if branch_text not in keyboards.branch_options:
        await update.message.reply_text("Խնդրում ենք ընտրել ցուցակից տրված մասնաճյուղերից մեկը։")
        return STATE_BRANCH

    context.user_data["branch"] = branch_text
    # Հարցնել որոնման ֆիլտրի տեսակը
    await update.message.reply_text(
        "Ընտրեք ֆիլտրի տեսակը կամ ընտրեք «Ամբողջը»՝ բոլոր հասանելի ժամերը դիտելու համար։",
        reply_markup=keyboards.filter_type_keyboard
    )
    return STATE_FILTER

# Handler for filter type selection
async def handle_filter_type(update, context):
    """Processes the chosen filter type (hour, date, weekday, or all)."""
    choice = update.message.text.strip().lower()
    # Ընտրել համապատասխան ուղղությունը՝ կախված օգտատիրոջ ընտրությունից
    if "ժամով" in choice:
        context.user_data["filter_type"] = "hour"
        # Հեռացնել ֆիլտրի ընտրության ստեղնաշարը և հարցնել ժամը
        await update.message.reply_text("Մուտքագրեք ցանկալի ժամը (օր.՝ 9 կամ 15):", reply_markup=ReplyKeyboardRemove())
        return STATE_HOUR
    elif "ամսաթվով" in choice:
        context.user_data["filter_type"] = "date"
        await update.message.reply_text("Մուտքագրեք կոնկրետ ամսաթիվ (օր.՝ 15.09.2025):", reply_markup=ReplyKeyboardRemove())
        return STATE_DATE
    elif "շաբաթվա" in choice:
        context.user_data["filter_type"] = "weekday"
        await update.message.reply_text("Մուտքագրեք շաբաթվա օր (օր.՝ Երկուշաբթի):", reply_markup=ReplyKeyboardRemove())
        return STATE_WEEKDAY
    elif "ամբողջ" in choice:
        # Առանց ֆիլտրի՝ ցուցադրել բոլոր հասանելի ժամերը
        exam_type = context.user_data.get("exam_type")
        branch = context.user_data.get("branch")
        filter_type = "all"
        filter_value = None
        # Ստանալ հասանելի ժամանակները (ամբողջ ցանկը)
        slots = scraper.get_available_slots(exam_type, branch, filter_type, filter_value)
        # Ֆորմավորել և ուղարկել արդյունքը
        if not slots:
            await update.message.reply_text("Նշված պայմաններով ազատ ժամեր չեն գտնվել։", reply_markup=ReplyKeyboardRemove())
        else:
            result_lines = [f"{date} - {time}" for date, time in slots]
            message_text = "Առկա ազատ ժամերը՝\n" + "\n".join(result_lines)
            await update.message.reply_text(message_text, reply_markup=ReplyKeyboardRemove())
        # Պահպանել որոնման մանրամասները բազայում
        user_id = context.user_data.get("user_id")
        db.add_search(user_id, exam_type, branch, filter_type, "")
        return ConversationHandler.END
    else:
        # Եթե անհասկանալի պատասխան է, կրկին հարցնել
        await update.message.reply_text("Խնդրում ենք ընտրել ֆիլտրի տարբերակը ցուցակից (Ժամով, Ամսաթվով, Շաբաթվա օրով, Ամբողջը):")
        return STATE_FILTER

# Handler for specific hour input
async def handle_hour_input(update, context):
    """Processes the hour filter input provided by the user."""
    text = update.message.text.strip()
    # Attempt to parse hour (ընդունել 0-23 միայն)
    match = re.match(r"^(\d{1,2})", text)
    hour_val = None
    if match:
        try:
            hour_val = int(match.group(1))
        except ValueError:
            hour_val = None
    if hour_val is None or hour_val < 0 or hour_val > 23:
        await update.message.reply_text("Խնդրում ենք մուտքագրել ժամը 0-ից 23 միջակայքում գտնվող ամբողջ թվով (օր.՝ 9 կամ 15):")
        return STATE_HOUR

    # Execute search with hour filter
    exam_type = context.user_data.get("exam_type")
    branch = context.user_data.get("branch")
    filter_type = "hour"
    filter_value = str(hour_val)
    slots = scraper.get_available_slots(exam_type, branch, filter_type, filter_value)
    if not slots:
        await update.message.reply_text("Նշված ժամին համապատասխան ազատ ժամեր չկան։")
    else:
        result_lines = [f"{date} - {time}" for date, time in slots]
        await update.message.reply_text("Հասանելի ժամեր այդ ժամին՝\n" + "\n".join(result_lines))
    # Save search record
    user_id = context.user_data.get("user_id")
    db.add_search(user_id, exam_type, branch, filter_type, filter_value)
    return ConversationHandler.END

# Handler for specific date input
async def handle_date_input(update, context):
    """Processes the specific date filter input."""
    date_text = update.message.text.strip()
    # Validate date format DD.MM.YYYY
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_text):
        await update.message.reply_text("Խնդրում ենք մուտքագրել ամսաթիվը ճիշտ ձևաչափով (օրինակ՝ 15.09.2025):")
        return STATE_DATE

    exam_type = context.user_data.get("exam_type")
    branch = context.user_data.get("branch")
    filter_type = "date"
    filter_value = date_text
    slots = scraper.get_available_slots(exam_type, branch, filter_type, filter_value)
    if not slots:
        await update.message.reply_text("Ընտրած ամսաթվով ազատ ժամեր չեն գտնվել։")
    else:
        result_lines = [f"{date} - {time}" for date, time in slots]
        await update.message.reply_text("Հասանելի ժամերը այդ օրը՝\n" + "\n".join(result_lines))
    # Պահպանել որոնումը բազայում
    user_id = context.user_data.get("user_id")
    db.add_search(user_id, exam_type, branch, filter_type, filter_value)
    return ConversationHandler.END

# Handler for weekday input
async def handle_weekday_input(update, context):
    """Processes the weekday filter input."""
    day_text = update.message.text.strip()
    # Ստուգել, որ օրվա անվանումը ճանաչված է (օրինակ՝ Երկուշաբթի)
    # Տեղափոխել փոքրատառերի, համեմատել հայտնի անվանումների հետ
    input_lower = day_text.lower()
    # Հայտնի շաբաթվա օրեր (հայերեն)
    weekdays_armenian = ["երկուշաբթի", "երեքշաբթի", "չորեքշաբթի", "հինգշաբթի", "ուրբաթ", "շաբաթ", "կիրակի"]
    if input_lower not in weekdays_armenian:
        await update.message.reply_text("Խնդրում ենք գրել շաբաթվա օրվա անվանումը ճիշտ (օրինակ՝ \"Երկուշաբթի\").")
        return STATE_WEEKDAY

    # Capitalize first letter for consistency
    # (Note: In Armenian, weekday names are often written in lowercase, but we'll standardize)
    filter_value = day_text.capitalize()
    exam_type = context.user_data.get("exam_type")
    branch = context.user_data.get("branch")
    filter_type = "weekday"
    slots = scraper.get_available_slots(exam_type, branch, filter_type, filter_value)
    if not slots:
        await update.message.reply_text("Նշված շաբաթվա օրվա համար ազատ ժամանակներ չեն գտնվել։")
    else:
        result_lines = [f"{date} - {time}" for date, time in slots]
        await update.message.reply_text(f"{filter_value} օրի հասանելի ժամերը՝\n" + "\n".join(result_lines))
    # Պահպանել որոնման հարցումը բազայում
    user_id = context.user_data.get("user_id")
    db.add_search(user_id, exam_type, branch, filter_type, filter_value)
    return ConversationHandler.END

# Cancel handler for both conversations
async def cancel(update, context):
    """Allows the user to cancel the conversation at any time."""
    await update.message.reply_text("Գործողությունը չեղարկված է։", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
