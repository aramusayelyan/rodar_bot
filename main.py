# main.py
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, ConversationHandler, CallbackContext
import config
import database
import scraper
import keyboards

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states for registration and searching
REG_PHONE, REG_SOCIAL, REG_CODE = range(3)
SEARCH_SERVICE, SEARCH_BRANCH, SEARCH_FILTER, SEARCH_WEEKDAY, SEARCH_DATE, SEARCH_HOUR, SEARCH_CONFIRM, SEARCH_EMAIL = range(8)

def start(update: Update, context: CallbackContext):
    """Handle the /start command - start registration if not already registered."""
    user_id = update.effective_user.id
    user = database.get_user(user_id)
    if user:
        # If already registered
        name = update.effective_user.first_name
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Բարև {name}։ Դուք արդեն գրանցված եք։\nՕգտագործեք /search որպեսզի որոնեք ազատ կտրոններ։")
        return ConversationHandler.END
    # Not registered: ask for phone number
    contact_button = KeyboardButton("Կիսվել հեռախոսահամարով", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Բարի գալուստ։ Խնդրում ենք ուղարկել Ձեր հեռախոսահամարը՝ գրանցվելու համար։",
                             reply_markup=reply_markup)
    return REG_PHONE

def receive_phone(update: Update, context: CallbackContext):
    """Handle receiving the user's phone number."""
    # The phone may come as contact or text
    phone = None
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
    context.user_data['phone'] = phone
    # Ask for social card number (Public Service Number)
    update.message.reply_text("Մուտքագրեք Ձեր սոցիալական քարտի համարը (ՀԾՀ):", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    return REG_SOCIAL

def receive_social(update: Update, context: CallbackContext):
    """Handle receiving the user's social card number (Public Service Number)."""
    social = update.message.text.strip()
    context.user_data['social'] = social
    # Initiate sending SMS code via scraper
    user_id = update.effective_user.id
    phone = context.user_data.get('phone')
    success = scraper.login_send_code(user_id, social, phone)
    if not success:
        update.message.reply_text("Խափանում տեղի ունեցավ SMS կոդ ուղարկելու ժամանակ։ Խնդրում ենք փորձել կրկին /start ։")
        return ConversationHandler.END
    # Ask for the SMS code
    update.message.reply_text("Խնդրում ենք մուտքագրել SMS-ով ստացված կոդը։")
    return REG_CODE

def receive_code(update: Update, context: CallbackContext):
    """Handle receiving the SMS verification code."""
    code = update.message.text.strip()
    user_id = update.effective_user.id
    phone = context.user_data.get('phone')
    social = context.user_data.get('social')
    success = scraper.login_verify_code(user_id, social, phone, code)
    if not success:
        update.message.reply_text("Ներմուծած կոդը սխալ է կամ սեշիան ընդհատվել է։ Խնդրում ենք կրկին փորձել /start ։")
        return ConversationHandler.END
    # Save user in database (no email yet, and save session cookies)
    cookies = scraper.get_session(user_id).cookies.get_dict()
    database.create_user(user_id, phone, social, email=None, cookies=cookies)
    update.message.reply_text("Գրանցումը հաջողությամբ ավարտվեց։ Այժմ կարող եք որոնել ազատ կտրոններ /search հրամանով։")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    """Cancel the conversation."""
    update.message.reply_text("Գործողությունը դադարեցվել է։")
    return ConversationHandler.END

def search_command(update: Update, context: CallbackContext):
    """Entry point for /search command."""
    user_id = update.effective_user.id
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text("Դուք դեռ գրանցված չեք։ Խնդրում ենք սեղմել /start սկզբում։")
        return ConversationHandler.END
    # Ask for service type
    update.message.reply_text("Ընտրեք ծառայությունը, որի համար ուզում եք հերթագրում անել։",
                              reply_markup=keyboards.build_menu(keyboards.SERVICE_OPTIONS, n_cols=1))
    return SEARCH_SERVICE

def select_service(update: Update, context: CallbackContext):
    """Handle service selection via inline keyboard."""
    query = update.callback_query
    query.answer()
    service_id = query.data
    context.user_data['service_id'] = service_id
    # Ask for branch
    query.edit_message_text("Ընտրեք ստորաբաժանումը (մասնաճյուղը):",
                             reply_markup=keyboards.build_menu(keyboards.BRANCH_OPTIONS, n_cols=1))
    return SEARCH_BRANCH

def select_branch(update: Update, context: CallbackContext):
    """Handle branch selection via inline keyboard."""
    query = update.callback_query
    query.answer()
    branch_id = query.data
    context.user_data['branch_id'] = branch_id
    # Ask for filter criteria
    query.edit_message_text("Ինչպե՞ս եք ուզում որոնել ազատ կտրոնները։",
                             reply_markup=keyboards.build_menu(keyboards.FILTER_OPTIONS, n_cols=1))
    return SEARCH_FILTER

def select_filter(update: Update, context: CallbackContext):
    """Handle filter criteria selection via inline keyboard."""
    query = update.callback_query
    query.answer()
    choice = query.data
    context.user_data['filter'] = choice
    if choice == "closest":
        # Find the closest available day (earliest slot overall)
        branch_id = context.user_data['branch_id']
        service_id = context.user_data['service_id']
        user = database.get_user(update.effective_user.id)
        cookies = user['cookies']
        # Check current month and next for availability
        from datetime import datetime
        today = datetime.now()
        found_date = None
        found_time = None
        for m_offset in range(0, 3):
            year = (today.year + ((today.month-1 + m_offset)//12))
            month = ((today.month-1 + m_offset) % 12) + 1
            days = scraper.fetch_available_days(update.effective_user.id, cookies, branch_id, service_id, year, month)
            days = [d for d in days if d >= today.strftime("%Y-%m-%d")]
            if days:
                # If found any available day in this period
                found_date = days[0]
                # Get first available time on that day
                times = scraper.fetch_available_times(update.effective_user.id, cookies, branch_id, service_id, found_date)
                if times:
                    found_time = times[0]
                else:
                    continue
                break
        if not found_date or not found_time:
            query.edit_message_text("Այս պահին ազատ կտրոններ չկան:")
            return ConversationHandler.END
        context.user_data['sel_date'] = found_date
        context.user_data['sel_time'] = found_time
        # Ask confirmation to book
        from datetime import datetime as dt
        human_date = dt.strptime(found_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        msg = f"Ամենամոտ հասանելի օրը՝ {human_date} ժամը {found_time}։ Գրանցվե՞լ այդ օրվա համար:"
        query.edit_message_text(msg, reply_markup=keyboards.build_menu([("Այո", "confirm_yes"), ("Ոչ", "confirm_no")], n_cols=2))
        return SEARCH_CONFIRM
    elif choice == "weekday":
        query.edit_message_text("Ընտրեք շաբաթվա օրը:", reply_markup=keyboards.build_menu(keyboards.WEEKDAY_OPTIONS, n_cols=1))
        return SEARCH_WEEKDAY
    elif choice == "date":
        query.edit_message_text("Մուտքագրեք ամսաթիվը (օրինակ՝ 25/08/2025):")
        return SEARCH_DATE
    elif choice == "hour":
        query.edit_message_text("Մուտքագրեք ժամը (0-23 միջակայքում, օրինակ՝ 14):")
        return SEARCH_HOUR
    elif choice == "all":
        # List all available upcoming slots
        branch_id = context.user_data['branch_id']
        service_id = context.user_data['service_id']
        user = database.get_user(update.effective_user.id)
        cookies = user['cookies']
        from datetime import datetime
        today = datetime.now()
        output_lines = []
        for m_offset in range(0, 2):
            year = (today.year + ((today.month-1 + m_offset)//12))
            month = ((today.month-1 + m_offset) % 12) + 1
            days = scraper.fetch_available_days(update.effective_user.id, cookies, branch_id, service_id, year, month)
            days = [d for d in days if d >= today.strftime("%Y-%m-%d")]
            for d in days:
                times = scraper.fetch_available_times(update.effective_user.id, cookies, branch_id, service_id, d)
                if times:
                    date_formatted = datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d")
                    times_str = ", ".join(times)
                    output_lines.append(f"{date_formatted}: {times_str}")
        if not output_lines:
            query.edit_message_text("Հասանելի ազատ կտրոններ չեն գտնվել առաջիկա ամսաթվերի համար:")
        else:
            query.edit_message_text("Ազատ ժամանակներ:\n" + "\n".join(output_lines))
        return ConversationHandler.END
    return ConversationHandler.END

def select_weekday(update: Update, context: CallbackContext):
    """Handle weekday selection and find next available date on that weekday."""
    query = update.callback_query
    query.answer()
    weekday_index = int(query.data)
    branch_id = context.user_data['branch_id']
    service_id = context.user_data['service_id']
    user = database.get_user(update.effective_user.id)
    cookies = user['cookies']
    from datetime import datetime, timedelta
    today = datetime.now()
    found_date = None
    found_time = None
    for day_offset in range(0, 90):
        date = today + timedelta(days=day_offset)
        if date.weekday() == weekday_index:
            date_str = date.strftime("%Y-%m-%d")
            times = scraper.fetch_available_times(update.effective_user.id, cookies, branch_id, service_id, date_str)
            if times:
                found_date = date_str
                found_time = times[0]
                break
    if not found_date:
        query.edit_message_text("Տրված շաբաթվա օրվա համար ազատ կտրոն չի գտնվել:")
        return ConversationHandler.END
    context.user_data['sel_date'] = found_date
    context.user_data['sel_time'] = found_time
    from datetime import datetime as dt
    human_date = dt.strptime(found_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    # Armenian weekday name from keyboards (tuple list)
    weekday_name = None
    for label, data in keyboards.WEEKDAY_OPTIONS:
        if data == str(weekday_index):
            weekday_name = label
            break
    msg = f"Առաջիկա {weekday_name} օրը՝ {human_date} ժամը {found_time}։ Գրանցվե՞լ այս պահին:"
    query.edit_message_text(msg, reply_markup=keyboards.build_menu([("Այո", "confirm_yes"), ("Ոչ", "confirm_no")], n_cols=2))
    return SEARCH_CONFIRM

def receive_date(update: Update, context: CallbackContext):
    """Handle user entering a specific date and list available times."""
    import re as regex
    text = update.message.text.strip()
    try:
        day, month, year = map(int, regex.split(r"[./-]", text))
        from datetime import datetime
        date_obj = datetime(year, month, day)
        date_str = date_obj.strftime("%Y-%m-%d")
    except Exception:
        update.message.reply_text("Ամսաթվի ձևաչափը անվավեր է։ Խնդրում ենք փորձել կրկին (օրինակ՝ 05/09/2025):")
        return SEARCH_DATE
    branch_id = context.user_data['branch_id']
    service_id = context.user_data['service_id']
    user = database.get_user(update.effective_user.id)
    cookies = user['cookies']
    times = scraper.fetch_available_times(update.effective_user.id, cookies, branch_id, service_id, date_str)
    if not times:
        update.message.reply_text(f"{date_str} օրը ազատ ժամանակներ չկան:")
    else:
        times_list = ", ".join(times)
        update.message.reply_text(f"{date_str} օրվա համար ազատ ժամանակներ են՝ {times_list}")
    return ConversationHandler.END

def receive_hour(update: Update, context: CallbackContext):
    """Handle user entering a preferred hour and find the earliest slot at that hour."""
    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("Խնդրում ենք մուտքագրել ժամը (նույնիսկ թվով):")
        return SEARCH_HOUR
    hour = int(text)
    if hour < 0 or hour > 23:
        update.message.reply_text("Խնդրում ենք մուտքագրել ժամը 0-ից 23 միջակայքում:")
        return SEARCH_HOUR
    branch_id = context.user_data['branch_id']
    service_id = context.user_data['service_id']
    user = database.get_user(update.effective_user.id)
    cookies = user['cookies']
    from datetime import datetime, timedelta
    now = datetime.now()
    found_date = None
    found_time = None
    for d in range(0, 90):
        date = now + timedelta(days=d)
        date_str = date.strftime("%Y-%m-%d")
        times = scraper.fetch_available_times(update.effective_user.id, cookies, branch_id, service_id, date_str)
        for t in times:
            try:
                t_hour = int(t.split(":")[0])
            except:
                continue
            if t_hour == hour:
                found_date = date_str
                found_time = t
                break
        if found_date:
            break
    if not found_date:
        update.message.reply_text(f"{hour}:00-ի հատվածում ազատ կտրոն չի գտնվել մոտակա ժամանակներում:")
        return ConversationHandler.END
    context.user_data['sel_date'] = found_date
    context.user_data['sel_time'] = found_time
    from datetime import datetime as dt
    human_date = dt.strptime(found_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    update.message.reply_text(f"Առաջին հասանելի ժամը {hour}-ին՝ {human_date} օրը, ժամը {found_time}։ Գրանցվե՞լ այս ժամանակի համար:",
                              reply_markup=keyboards.build_menu([("Այո", "confirm_yes"), ("Ոչ", "confirm_no")], n_cols=2))
    return SEARCH_CONFIRM

def confirm_booking(update: Update, context: CallbackContext):
    """Handle the confirmation of booking (Yes/No)."""
    query = update.callback_query
    query.answer()
    if query.data == "confirm_no":
        query.edit_message_text("Գործողությունը չեղարկվեց։")
        return ConversationHandler.END
    # If yes, proceed to book. Check if we have email
    user_record = database.get_user(update.effective_user.id)
    if not user_record.get('email'):
        # Ask for email
        query.edit_message_text("Խնդրում ենք մուտքագրել Ձեր էլ. փոստի հասցեն գրանցումը հաստատելու համար:")
        return SEARCH_EMAIL
    # We have email, perform booking
    branch_id = context.user_data['branch_id']
    service_id = context.user_data['service_id']
    date_str = context.user_data['sel_date']
    time_str = context.user_data['sel_time']
    email = user_record['email']
    cookies = user_record['cookies']
    success = scraper.book_appointment(update.effective_user.id, cookies, branch_id, service_id, date_str, time_str, email)
    if success:
        query.edit_message_text("Ձեր հերթագրումը հաջողությամբ գրանցվեց։Խնդրում ենք չմոռանալ ակտիվացնել այն համապատասխան բաժնում։")
    else:
        query.edit_message_text("Ձեռքբերմանը չհաջողվեց։ Հնարավոր է, որ կտրոնն արդեն զբաղված է կամ համակարգում սխալ առաջացավ։")
    return ConversationHandler.END

def receive_email(update: Update, context: CallbackContext):
    """Receive the user's email address for booking and complete the booking."""
    email = update.message.text.strip()
    # Update email in database
    user_id = update.effective_user.id
    database.update_user(user_id, {"email": email})
    # Now perform booking with the stored slot info
    branch_id = context.user_data['branch_id']
    service_id = context.user_data['service_id']
    date_str = context.user_data['sel_date']
    time_str = context.user_data['sel_time']
    user_record = database.get_user(user_id)
    cookies = user_record['cookies']
    success = scraper.book_appointment(user_id, cookies, branch_id, service_id, date_str, time_str, email)
    if success:
        update.message.reply_text("Ձեր հերթագրումը հաջողությամբ գրանցվեց։ Խնդրում ենք ներկայանալ նշված օրը համապատասխան մասնաճյուղ։")
    else:
        update.message.reply_text("Կտրոնի ամրագրումը չհաջողվեց։ Կարող է այն արդեն զբաղված էր։")
    return ConversationHandler.END

def main():
    updater = Updater(token=config.BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    # Conversation handler for registration
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REG_PHONE: [MessageHandler(Filters.contact | Filters.text, receive_phone)],
            REG_SOCIAL: [MessageHandler(Filters.text & ~Filters.command, receive_social)],
            REG_CODE: [MessageHandler(Filters.text & ~Filters.command, receive_code)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    # Conversation handler for searching and booking
    search_conv = ConversationHandler(
        entry_points=[CommandHandler('search', search_command)],
        states={
            SEARCH_SERVICE: [CallbackQueryHandler(select_service, pattern=r'^\d{6}$')],
            SEARCH_BRANCH: [CallbackQueryHandler(select_branch, pattern=r'^\d+$')],
            SEARCH_FILTER: [CallbackQueryHandler(select_filter, pattern='^(closest|weekday|date|hour|all)$')],
            SEARCH_WEEKDAY: [CallbackQueryHandler(select_weekday, pattern=r'^[0-6]$')],
            SEARCH_DATE: [MessageHandler(Filters.text & ~Filters.command, receive_date)],
            SEARCH_HOUR: [MessageHandler(Filters.text & ~Filters.command, receive_hour)],
            SEARCH_CONFIRM: [CallbackQueryHandler(confirm_booking, pattern='^confirm_(yes|no)$')],
            SEARCH_EMAIL: [MessageHandler(Filters.text & ~Filters.command, receive_email)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(reg_conv)
    dispatcher.add_handler(search_conv)
    dispatcher.add_handler(CommandHandler('cancel', cancel))
    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
