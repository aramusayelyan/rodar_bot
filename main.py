#!/usr/bin/env python3
import logging
import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, filters
import config
import keyboards
import scraper

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation state constants
PHONE, BRANCH, EXAM_TYPE, FILTER_METHOD, FILTER_VALUE = range(5)

def start(update: Update, context: CallbackContext):
    """Handle /start command, begin conversation by asking for phone contact."""
    user = update.effective_user
    # Greeting message and ask for phone number
    contact_button = KeyboardButton("📱 Ուղարկել հեռախոսահամարս", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        f"Բարի օր, {user.first_name if user else 'Օգտագործող'}։\n"
        "Խնդրում եմ կիսվել Ձեր հեռախոսահամարով՝ շարունակելու համար։",
        reply_markup=reply_markup
    )
    return PHONE

def handle_contact(update: Update, context: CallbackContext):
    """Receive user's contact (phone number) and proceed to ask for branch."""
    contact = update.message.contact
    # We have the phone number (contact.phone_number) if needed for verification
    # Proceed to ask branch selection
    reply_markup = keyboards.branch_markup
    update.message.reply_text(
        "Շնորհակալություն։ Հիմա ընտրեք հաշվառման-քննական բաժանմունքը։",
        reply_markup=reply_markup
    )
    return BRANCH

def handle_branch(update: Update, context: CallbackContext):
    """Handle branch selection, ask for exam type."""
    branch = update.message.text
    context.user_data["branch"] = branch
    # Ask for exam type
    reply_markup = keyboards.exam_type_markup
    update.message.reply_text(
        "Ընտրեք քննության տեսակը։",
        reply_markup=reply_markup
    )
    return EXAM_TYPE

def handle_exam_type(update: Update, context: CallbackContext):
    """Handle exam type selection, ask for filter method."""
    exam_type = update.message.text
    # Strip the word "քննություն" if present for internal use
    if exam_type.endswith("քննություն"):
        exam_type = exam_type.replace(" քննություն", "")
    context.user_data["exam_type"] = exam_type
    # Ask for filter method
    reply_markup = keyboards.filter_method_markup
    update.message.reply_text(
        "Ընտրեք ազատ ժամանակների ֆիլտրի տարբերակը։",
        reply_markup=reply_markup
    )
    return FILTER_METHOD

def handle_filter_method(update: Update, context: CallbackContext):
    """Handle filter method choice, possibly ask for further filter detail or fetch results."""
    choice = update.message.text
    choice = choice.strip()
    # Determine which filter user chose
    if choice.startswith("Բոլոր"):
        # No filtering - fetch all slots
        branch = context.user_data["branch"]
        exam_type = context.user_data["exam_type"]
        result_text = scraper.fetch_available_slots(branch, exam_type)
        # If no slots found, scraper should return appropriate message
        update.message.reply_text(result_text or "Ազատ ժամեր չեն գտնվել։")
        return ConversationHandler.END
    elif "շաբաթվա" in choice:
        context.user_data["filter_type"] = "weekday"
        # Ask which weekday
        reply_markup = keyboards.weekdays_markup
        update.message.reply_text(
            "Ընտրեք շաբաթվա օրը (Երկուշաբթի - Կիրակի)։",
            reply_markup=reply_markup
        )
        return FILTER_VALUE
    elif "ամսաթվի" in choice:
        context.user_data["filter_type"] = "date"
        update.message.reply_text(
            "Մուտքագրեք ցանկալի ամսաթիվը ֆորմատով ՕՕ.ԱԱԱԱ (օրինակ՝ 15.09.2025):",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True)
        )
        return FILTER_VALUE
    elif "ժամի" in choice:
        context.user_data["filter_type"] = "hour"
        update.message.reply_text(
            "Մուտքագրեք ցանկալի ժամը ֆորմատով ԺԺ:ՐՐ (օրինակ՝ 09:00):",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True)
        )
        return FILTER_VALUE
    else:
        # Unknown choice, ask again
        update.message.reply_text("Խնդրում եմเลือก մատչելի տարբերակներից։")
        return FILTER_METHOD

def handle_filter_value(update: Update, context: CallbackContext):
    """Handle the specific filter value (weekday/date/hour) from user and fetch results."""
    filter_type = context.user_data.get("filter_type")
    user_input = update.message.text.strip()
    branch = context.user_data["branch"]
    exam_type = context.user_data["exam_type"]
    # Initialize filter parameters for scraper
    weekday = None
    date = None
    hour = None
    if filter_type == "weekday":
        # Map Armenian weekday name to number 0-6 (Monday=0, Sunday=6)
        weekdays_map = {
            "Երկուշաբթի": 0,
            "Երեքշաբթի": 1,
            "Չորեքշաբթի": 2,
            "Հինգշաբթի": 3,
            "Ուրբաթ": 4,
            "Շաբաթ": 5,
            "Կիրակի": 6
        }
        if user_input not in weekdays_map:
            update.message.reply_text("Խնդրում ենք ընտրել շաբաթվա օրվա անվանումը տրված ցուցակից։")
            return FILTER_VALUE
        weekday = weekdays_map[user_input]
    elif filter_type == "date":
        # Expect format dd.mm.yyyy
        try:
            parts = user_input.split(".")
            if len(parts) != 3:
                raise ValueError
            day = int(parts[0]); month = int(parts[1]); year = int(parts[2])
            date = f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{parts[2]}"
        except Exception as e:
            update.message.reply_text("Խնդրում էք մուտքագրել ամսաթիվը ճիշտ ֆորմատով (օրինակ՝ 05.10.2025):")
            return FILTER_VALUE
    elif filter_type == "hour":
        # Expect format HH:MM
        if not (len(user_input) == 5 and user_input[2] == ':' and user_input[:2].isdigit() and user_input[3:].isdigit()):
            update.message.reply_text("Խնդրում ենք մուտքագրել ժամը ճիշտ ֆորմատով (օրինակ՝ 09:30):")
            return FILTER_VALUE
        hour = user_input
    # Fetch and format results with the given filters
    result_text = scraper.fetch_available_slots(branch, exam_type, weekday=weekday, specific_date=date, specific_hour=hour)
    if not result_text:
        result_text = "Նման ֆիլտրով համապատասխան ազատ ժամանակներ չեն գտնվել։"
    update.message.reply_text(result_text)
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    """Allow user to cancel the conversation."""
    update.message.reply_text("Գործընթացը դադարեցվեց։")
    return ConversationHandler.END

def main():
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    # Define conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, handle_contact)],
            BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_branch)],
            EXAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exam_type)],
            FILTER_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filter_method)],
            FILTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filter_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    # Start the bot (polling)
    application.run_polling(stop_signals=None)  # disable built-in signal handlers in Render environment

if __name__ == "__main__":
    main()
