import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters
from telegram.ext import CallbackQueryHandler  # (Not used here, but available for inline keyboards if needed)
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Import custom modules
import config
from handlers import (
    start_command, handle_contact, handle_social, handle_code,
    search_command, handle_exam_type, handle_branch, handle_filter_type,
    handle_hour_input, handle_date_input, handle_weekday_input,
    cancel
)
from handlers import (
    STATE_PHONE, STATE_SOCIAL, STATE_CODE,
    STATE_EXAM, STATE_BRANCH, STATE_FILTER, STATE_HOUR, STATE_DATE, STATE_WEEKDAY
)

def main():
    """Հիմնական գործառույթ, որը մեկնարկում է Telegram բոտը։"""
    # Set up logging to stdout
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot...")

    # Initialize the bot application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Define conversation handler for /start (registration flow)
    start_conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            STATE_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, handle_contact)],
            STATE_SOCIAL: [MessageHandler(filters.TEXT, handle_social)],
            STATE_CODE: [MessageHandler(filters.TEXT, handle_code)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    # Define conversation handler for /search (slot search flow)
    search_conversation = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            STATE_EXAM: [MessageHandler(filters.TEXT, handle_exam_type)],
            STATE_BRANCH: [MessageHandler(filters.TEXT, handle_branch)],
            STATE_FILTER: [MessageHandler(filters.TEXT, handle_filter_type)],
            STATE_HOUR: [MessageHandler(filters.TEXT, handle_hour_input)],
            STATE_DATE: [MessageHandler(filters.TEXT, handle_date_input)],
            STATE_WEEKDAY: [MessageHandler(filters.TEXT, handle_weekday_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    # Register handlers with the application
    application.add_handler(start_conversation)
    application.add_handler(search_conversation)
    # Optionally, add a /help command handler (not strictly required but useful)
    application.add_handler(CommandHandler("help", lambda update, ctx: update.message.reply_text(
        "Օգտագործեք /start՝ գրանցվելու համար և /search՝ ազատ ժամեր փնտրելու համար։"
    )))

    # Run the bot until Ctrl+C
    application.run_polling()

if __name__ == "__main__":
    main()
