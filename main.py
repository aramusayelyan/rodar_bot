import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# Import custom modules
import config
import scraper
import keyboards

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
STATE_SECTION, STATE_EXAM_TYPE, STATE_FILTER_CHOICE, STATE_DAY_SELECT, STATE_DATE_INPUT, STATE_HOUR_INPUT = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a welcome message and prompt for selecting a section (branch)."""
    await update.message.reply_text(
        "Բարի գալուստ։ Խնդրում եմ ընտրել բաժինը․",
        reply_markup=keyboards.section_menu  # ReplyKeyboardMarkup for sections
    )
    return STATE_SECTION

async def section_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle section selection from reply keyboard."""
    section_name = update.message.text
    # Validate selection
    if section_name not in keyboards.SECTION_NAMES_ARM:
        await update.message.reply_text("Խնդրում եմ ընտրել ցանկից տրված բաժիններից։")
        return STATE_SECTION
    # Save the chosen section (store English code for internal use)
    section_code = keyboards.SECTION_NAME_TO_CODE.get(section_name)
    context.user_data["section"] = section_code
    # Ask for exam type (theory or practical)
    await update.message.reply_text(
        "Ընտրեք քննության տեսակը․",
        reply_markup=InlineKeyboardMarkup(keyboards.exam_type_buttons)
    )
    return STATE_EXAM_TYPE

async def exam_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle exam type selection via inline keyboard."""
    query = update.callback_query
    await query.answer()
    choice = query.data  # e.g. "type_theory" or "type_practical"
    # Save exam type choice
    exam_type = "theory" if choice == "type_theory" else "practical"
    context.user_data["exam_type"] = exam_type
    # Prompt for filter (day, date, hour, or no filter)
    await query.message.reply_text(
        "Պահանջվող տվյալները քաղել ըստ՝",
        reply_markup=InlineKeyboardMarkup(keyboards.filter_type_buttons)
    )
    return STATE_FILTER_CHOICE

async def filter_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle filter type selection via inline keyboard."""
    query = update.callback_query
    await query.answer()
    choice = query.data  # e.g. "filter_day", "filter_date", "filter_hour", "filter_none"
    if choice == "filter_none":
        # No filter – fetch data directly
        section = context.user_data["section"]
        exam_type = context.user_data["exam_type"]
        result_text = scraper.fetch_data(section, exam_type)
        await query.message.reply_text(result_text)
        return ConversationHandler.END
    elif choice == "filter_day":
        # Ask for day of week
        await query.message.reply_text(
            "Ընտրեք շաբաթվա օրը․",
            reply_markup=InlineKeyboardMarkup(keyboards.weekday_buttons)
        )
        return STATE_DAY_SELECT
    elif choice == "filter_date":
        # Prompt user to input a specific date
        await query.message.reply_text("Մուտքագրեք ամսաթիվը (Օր.Мիս.Тարիք ձևաչափով, օրինակ՝ 25.08.2025):")
        return STATE_DATE_INPUT
    elif choice == "filter_hour":
        # Prompt user to input specific hour (HH:MM format)
        await query.message.reply_text("Մուտքագրեք ժամը (Օրինակ՝ 10:00):")
        return STATE_HOUR_INPUT

async def day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle specific weekday selection via inline keyboard."""
    query = update.callback_query
    await query.answer()
    # Map callback data like "day_0" to weekday number
    day_index = int(query.data.split("_")[1])  # 0=Monday, 6=Sunday
    context.user_data["filter_day"] = day_index
    # Fetch data filtered by weekday
    section = context.user_data["section"]
    exam_type = context.user_data["exam_type"]
    result_text = scraper.fetch_data(section, exam_type, filter_day=day_index)
    await query.message.reply_text(result_text)
    return ConversationHandler.END

async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle specific date input by user."""
    date_text = update.message.text.strip()
    context.user_data["filter_date"] = date_text
    # Fetch data for that date
    section = context.user_data["section"]
    exam_type = context.user_data["exam_type"]
    result_text = scraper.fetch_data(section, exam_type, filter_date=date_text)
    await update.message.reply_text(result_text)
    return ConversationHandler.END

async def hour_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle specific hour input by user."""
    hour_text = update.message.text.strip()
    context.user_data["filter_hour"] = hour_text
    # Fetch data filtered by hour
    section = context.user_data["section"]
    exam_type = context.user_data["exam_type"]
    result_text = scraper.fetch_data(section, exam_type, filter_hour=hour_text)
    await update.message.reply_text(result_text)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allow user to cancel the conversation."""
    await update.message.reply_text("Գործողությունը չեղարկվել է։")
    return ConversationHandler.END

def main():
    # Initialize bot application with token
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    # Set up conversation handler for the booking query flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_SECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, section_chosen)],
            STATE_EXAM_TYPE: [CallbackQueryHandler(exam_type_chosen, pattern=r"^type_")],
            STATE_FILTER_CHOICE: [CallbackQueryHandler(filter_chosen, pattern=r"^filter_")],
            STATE_DAY_SELECT: [CallbackQueryHandler(day_selected, pattern=r"^day_")],
            STATE_DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_entered)],
            STATE_HOUR_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hour_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)

    # Start polling updates
    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
