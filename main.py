from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

from config import TOKEN
from keyboards import branch_keyboard, exam_keyboard, filter_keyboard, weekday_keyboard, contact_request_keyboard
from scraper import get_available_slots

# Define conversation states
PHONE, BRANCH, EXAM, FILTER, WEEKDAY, DATE_INPUT, HOUR_INPUT = range(7)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command: ask for phone if not provided, else jump to branch selection."""
    user = update.effective_user
    # Greet the user
    await update.message.reply_text(f"Բարի գալուստ, {user.first_name}։\n")
    # Check if we already have the phone number for this user
    if context.user_data.get("phone"):
        # Phone is already stored; skip asking again
        await update.message.reply_text(
            "Անձնական հեռախոսահամարը արդեն պահպանված է։",
        )
        # Proceed to branch selection
        await update.message.reply_text(
            "Խնդրում ենք ընտրել մասնաճյուղը․",
            reply_markup=branch_keyboard()
        )
        return BRANCH
    else:
        # Request contact (phone number) from the user
        await update.message.reply_text(
            "Խնդրում ենք կիսվել ձեր հեռախոսահամարով՝ սկսելուն համապատասխան.",
            reply_markup=contact_request_keyboard
        )
        # Next state will be PHONE, expecting contact
        return PHONE

# Handler for receiving contact (phone number)
async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the received phone number and ask for branch selection."""
    contact = update.message.contact
    if contact is None:
        # User did not share contact, prompt again or allow manual entry
        await update.message.reply_text("Խնդրում ենք ուղարկել ձեր հեռախոսահամարը։")
        return PHONE
    # Store phone number
    context.user_data["phone"] = contact.phone_number
    # Acknowledge and proceed
    await update.message.reply_text("Շնորհակալություն։ Ձեր հեռախոսահամարը պահպանված է։")
    # Ask for branch selection
    await update.message.reply_text(
        "Խնդրում ենք ընտրել քննության անցկացման բաժինը․",
        reply_markup=branch_keyboard()
    )
    return BRANCH

# Handler for branch selection (callback query from inline keyboard)
async def branch_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store selected branch and ask for exam type."""
    query = update.callback_query
    await query.answer()  # acknowledge the callback
    data = query.data  # e.g. "branch:33"
    # Parse branch ID
    try:
        branch_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("Կատարվել է սխալ մասնաճյուղի ընտրության մեջ։ Խնդրում ենք կրկին փորձել։")
        return ConversationHandler.END
    # Store branch selection
    context.user_data["branch_id"] = branch_id
    # Retrieve branch name for confirmation (find in BRANCHES list)
    branch_name = next((name for name, bid in context.bot_data.get("branches_list", []) if bid == branch_id), None)
    if not branch_name:
        # If not stored in bot_data, try to get from keyboards list
        for name, bid in context.bot_data.get("branches_list", []):
            if bid == branch_id:
                branch_name = name
                break
    if not branch_name:
        branch_name = "Ընտրված մասնաճյուղ"
    # Acknowledge selection
    await query.edit_message_text(f"Ընտրված մասնաճյուղը՝ {branch_name}։")
    # Ask for exam type
    await query.edit_message_text(
        f"{branch_name} - Խնդրում ենք ընտրել քննության տեսակը․",
        reply_markup=exam_keyboard()
    )
    return EXAM

# Handler for exam type selection
async def exam_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store exam type and ask for filter options."""
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g. "exam:300691"
    try:
        service_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("Սխալ քննության տեսակ։ Խնդրում ենք սկսել սկզբից։")
        return ConversationHandler.END
    context.user_data["service_id"] = service_id
    exam_name = "տեսական" if service_id == 300691 else "գործնական"
    # Confirm the choice
    await query.edit_message_text(f"Ընտրված քննության տեսակը՝ { 'Տեսական' if service_id==300691 else 'Գործնական' }։")
    # Ask for filter option
    await query.edit_message_text(
        "Ինչպե՞ս եք ցանկանում դիտել ազատ ժամանակները։ Ընտրեք ֆիլտրի տարբերակը․",
        reply_markup=filter_keyboard()
    )
    return FILTER

# Handler for filter selection
async def filter_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the filter type selection and either ask for further detail or fetch slots."""
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":")[1]  # "weekday", "date", "hour", or "all"
    context.user_data["filter"] = choice
    if choice == "weekday":
        # Ask which weekday
        await query.edit_message_text("Խնդրում ենք ընտրել շաբաթվա օրը․", reply_markup=weekday_keyboard())
        return WEEKDAY
    elif choice == "date":
        # Ask user to type a specific date
        await query.edit_message_text("Խնդրում եմ մուտքագրել ամսաթիվը (օր.` 25.12.2025 ):")
        return DATE_INPUT
    elif choice == "hour":
        # Ask user to provide hour
        await query.edit_message_text("Խնդրում եմ մուտքագրել ժամը (0-23 միջակայքում, օրինակ՝ 9 կամ 15)՝:")
        return HOUR_INPUT
    elif choice == "all":
        # No further input needed, we can fetch all available slots
        # But we must edit message to remove inline buttons
        await query.edit_message_text("Բոլոր առկա ազատ ժամերը ստուգվում են․․․")
        # Proceed to fetch data
        return await fetch_and_send_slots(update, context)
    else:
        # Unknown filter option
        await query.edit_message_text("Անհայտ ընտրություն։ Սկսեք սկզբից /start հրամանով։")
        return ConversationHandler.END

# Handler for weekday selection
async def weekday_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store selected weekday and fetch slots filtered by that weekday."""
    query = update.callback_query
    await query.answer()
    try:
        weekday_index = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("Սխալ շաբաթվա օր։")
        return ConversationHandler.END
    context.user_data["weekday_index"] = weekday_index
    # Acknowledge weekday choice
    weekday_name = ["Երկուշաբթի","Երեքշաբթի","Չորեքշաբթի","Հինգշաբթի","Ուրբաթ","Շաբաթ","Կիրակի"][weekday_index]
    await query.edit_message_text(f"Ընտրված շաբաթվա օրը՝ {weekday_name}։ Ազատ ժամերի ստուգում․․․")
    # Proceed to fetch data
    return await fetch_and_send_slots(update, context)

# Handler for date input
async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse the entered date and fetch slots for that date."""
    text = update.message.text.strip()
    # Expecting format DD.MM.YYYY
    try:
        day, month, year = map(int, text.replace("/", ".").split("."))
        query_date = datetime(year, month, day).date()
    except Exception as e:
        await update.message.reply_text("Խնդրում ենք մուտքագրել ամսաթիվը ճիշտ ձևաչափով (օր. 05.09.2025):")
        return DATE_INPUT
    context.user_data["query_date"] = query_date
    await update.message.reply_text(f"Ընտրված ամսաթիվը՝ {query_date.strftime('%d.%m.%Y')}։ Ստուգվում է առկայությունը․․․")
    # Proceed to fetch data
    return await fetch_and_send_slots(update, context)

# Handler for hour input
async def hour_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the hour filter and fetch slots at that hour."""
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Խնդրում ենք մուտքագրել ժամը՝ թվով (օր. 9 կամ 15):")
        return HOUR_INPUT
    hour = int(text)
    if hour < 0 or hour > 23:
        await update.message.reply_text("Ժամը պետք է լինի 0-23 միջակայքում։ Խնդրում ենք կրկին փորձել:")
        return HOUR_INPUT
    context.user_data["hour"] = hour
    await update.message.reply_text(f"Ընտրված ժամը՝ {hour}:00-ի միջակայք։ Ստուգվում է ազատ ժամերը․․․")
    # Proceed to fetch data
    return await fetch_and_send_slots(update, context)

# Function to fetch slots using scraper and send the result message
async def fetch_and_send_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch available slots based on stored user criteria and send the result message."""
    # Get stored selections
    branch_id = context.user_data.get("branch_id")
    service_id = context.user_data.get("service_id")
    filter_type = context.user_data.get("filter")
    if not branch_id or not service_id:
        # Something went wrong; end conversation
        await update.callback_query.edit_message_text("Տեղի ունեցավ սխալ։ Խնդրում ենք սկսել սկզբից։")
        return ConversationHandler.END
    # Fetch all available slots for that branch & service
    slots = get_available_slots(branch_id, service_id)
    # Filter the slots as per user's choice
    if filter_type == "weekday":
        idx = context.user_data.get("weekday_index")
        if idx is not None:
            slots = [slot for slot in slots if slot[0].weekday() == idx]
    elif filter_type == "date":
        q_date = context.user_data.get("query_date")
        if q_date:
            slots = [slot for slot in slots if slot[0] == q_date]
    elif filter_type == "hour":
        hr = context.user_data.get("hour")
        if hr is not None:
            slots = [slot for slot in slots if int(slot[1].split(":")[0]) == hr]
    # Prepare message with results
    if not slots:
        msg = "Ցավոք, տվյալ հարցմամբ ազատ ժամանակներ չեն գտնվել։"
    else:
        # Format the list of slots
        lines = []
        # Optionally, include the branch and exam info in header
        branch_name = next((name for name, bid in context.bot_data.get("branches_list", []) if bid == branch_id), "")
        exam_name = "տեսական" if service_id == 300691 else "գործնական"
        header = f"Ազատ ժամեր {branch_name} բաժնում ({'տեսական' if service_id==300691 else 'գործնական'} քննություն):\n"
        lines.append(header)
        for date_obj, time_str in slots:
            # Format date as DD MonthName YYYY in Armenian
            month_names = ["Հունվար","Փետրվար","Մարտ","Ապրիլ","Մայիս","Հունիս",
                           "Հուլիս","Օգոստոս","Սեպտեմբեր","Հոկտեմբեր","Նոյեմբեր","Դեկտեմբեր"]
            day = date_obj.day
            month_name = month_names[date_obj.month - 1]
            year = date_obj.year
            lines.append(f" - {day} {month_name} {year}, ժամը {time_str}")
        msg = "\n".join(lines)
    # Send the message to user
    if update.callback_query:
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)
    # End of conversation
    return ConversationHandler.END

# Handler to cancel the conversation (optional)
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Գործողությունը չեղարկված է։")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()
    # Save branch list in bot_data for lookup (for names in messages)
    application.bot_data["branches_list"] = [(name, bid) for name, bid in BRANCHES]  # from keyboards.py BRANCHES
    
    # Set up conversation handler with states and handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, phone_received)],
            BRANCH: [CallbackQueryHandler(branch_chosen, pattern="^branch:")],
            EXAM: [CallbackQueryHandler(exam_chosen, pattern="^exam:")],
            FILTER: [CallbackQueryHandler(filter_chosen, pattern="^filter:")],
            WEEKDAY: [CallbackQueryHandler(weekday_selected, pattern="^weekday:")],
            DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_entered)],
            HOUR_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hour_entered)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(conv_handler)
    # Also add a direct command to check slots quickly
    application.add_handler(CommandHandler("slots", 
        lambda update, context: context.application.create_task(handle_slots_command(update, context))
    ))
    
    # Start the bot
    print("Bot is polling for updates...")
    application.run_polling()

# Direct /slots command handler (outside conversation)
async def handle_slots_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows user to fetch slots without repeating selections, using stored data."""
    # If we have branch and service stored for this user, use them; otherwise prompt to use /start
    if "branch_id" in context.user_data and "service_id" in context.user_data:
        await update.message.reply_text("Վերջին պահպանված հարցումով ազատ ժամանակները բերվում են...")
        # Use last filter if available, else default to all
        # For simplicity, we'll just fetch all for last branch & exam
        branch_id = context.user_data["branch_id"]
        service_id = context.user_data["service_id"]
        slots = get_available_slots(branch_id, service_id)
        if not slots:
            await update.message.reply_text("Այս պահին ազատ ժամանակներ չկան ձեր պահպանված հարցման համար։")
        else:
            lines = []
            branch_name = next((name for name, bid in context.bot_data.get("branches_list", []) if bid == branch_id), "")
            header = f"Ազատ ժամեր {branch_name} բաժնում ({'տեսական' if service_id==300691 else 'գործնական'} քննություն):\n"
            lines.append(header)
            for date_obj, time_str in slots:
                month_names = ["Հունվար","Փետրվար","Մարտ","Ապրիլ","Մայիս","Հունիս",
                               "Հուլիս","Օգոստոս","Սեպտեմբեր","Հոկտեմբեր","Նոյեմբեր","Դեկտեմբեր"]
                day = date_obj.day
                month_name = month_names[date_obj.month - 1]
                year = date_obj.year
                lines.append(f" - {day} {month_name} {year}, ժամը {time_str}")
            msg = "\n".join(lines)
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Խնդրում ենք նախ սկսել /start հրամանով և կատարել ընտրությունները։")
