import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes,
    filters
)
from scraper import fetch_available_slots  # custom scraper function
from keyboards import BRANCH_OPTIONS, EXAM_TYPE_OPTIONS, FILTER_TYPE_OPTIONS, WEEKDAY_OPTIONS
from config import TELEGRAM_TOKEN

# Conversation state constants
PHONE, BRANCH, EXAM_TYPE, FILTER_TYPE, WEEKDAY = range(5)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a welcome message and ask for the user's phone number (contact share)."""
    user = update.effective_user
    # Create a reply keyboard with a button to share contact
    contact_button = KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    # Greeting the user and prompting for phone number
    await update.message.reply_text(
        f"Բարի գալուստ, {user.first_name or 'օգտատեր'}։ Խնդրում ենք ուղարկել ձեր հեռախոսահամարը՝ շարունակելու համար։",
        reply_markup=reply_markup
    )
    return PHONE

# Handler for receiving phone number (as contact or text)
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the user's phone number and ask for the preferred exam center (branch)."""
    contact = update.message.contact
    if contact is not None:
        phone_number = contact.phone_number
    else:
        phone_number = update.message.text
    context.user_data['phone'] = phone_number
    # Prepare branch selection keyboard (Armenian branch names)
    branches = [list(group) for group in BRANCH_OPTIONS]  # BRANCH_OPTIONS is a list of lists for rows
    reply_markup = ReplyKeyboardMarkup(branches, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Խնդրում ենք ընտրել հաշվառման-քննական բաժինը։", reply_markup=reply_markup)
    return BRANCH

# Handler for branch selection
async def handle_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save selected branch and ask for exam type."""
    branch = update.message.text
    context.user_data['branch'] = branch
    exam_types = [EXAM_TYPE_OPTIONS]  # single row with both exam types
    reply_markup = ReplyKeyboardMarkup(exam_types, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Ընտրեք քննության տեսակը։", reply_markup=reply_markup)
    return EXAM_TYPE

# Handler for exam type selection
async def handle_exam_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save exam type and ask for filter preference."""
    exam_type = update.message.text
    context.user_data['exam_type'] = exam_type
    filters = [FILTER_TYPE_OPTIONS]  # single row of filter choices
    reply_markup = ReplyKeyboardMarkup(filters, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Ինչպես ցուցադրել արդյունքները՞", reply_markup=reply_markup)
    return FILTER_TYPE

# Handler for filter type selection
async def handle_filter_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save filter type. If filtering by weekday, ask for weekday; otherwise fetch results."""
    filter_choice = update.message.text
    context.user_data['filter_type'] = filter_choice
    if filter_choice == "Ըստ շաբաթվա օրվա":
        # Ask which weekday
        weekdays = [WEEKDAY_OPTIONS[:3], WEEKDAY_OPTIONS[3:6], WEEKDAY_OPTIONS[6:]]  # split into rows
        reply_markup = ReplyKeyboardMarkup(weekdays, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Ընտրեք նախընտրելի շաբաթվա օրը։", reply_markup=reply_markup)
        return WEEKDAY
    else:
        # No specific weekday filter; proceed to fetch slots
        await provide_results(update, context)
        return ConversationHandler.END

# Handler for weekday selection (only if that filter was chosen)
async def handle_weekday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save chosen weekday and fetch filtered results."""
    weekday = update.message.text  # e.g., "Երկուշաբթի"
    context.user_data['weekday'] = weekday
    # Proceed to fetch slots with weekday filter
    await provide_results(update, context)
    return ConversationHandler.END

# Function to fetch slots and send result to user
async def provide_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch available slots via scraper and send the filtered results back to the user."""
    user_data = context.user_data
    branch = user_data.get('branch')
    exam_type = user_data.get('exam_type')
    filter_type = user_data.get('filter_type')
    weekday = user_data.get('weekday') if filter_type == "Ըստ շաբաթվա օրվա" else None

    # Indicate that we are searching
    await update.message.reply_text("🔍 Խնդրում ենք սպասել, տվյալները ստուգվում են...")

    # Call the scraper in a non-blocking way
    slots = await asyncio.to_thread(fetch_available_slots, branch, exam_type)

    if slots is None:
        # Scraper encountered an error (e.g., site unreachable)
        await update.message.reply_text("Ներողություն, տվյալները չէ հաջողվում ստանալ կայքից։")
        return

    # Filter slots based on user preference
    filtered = slots
    if slots and filter_type == "Ըստ շաբաթվա օրվա":
        # Filter by specific weekday name (e.g., only Monday slots)
        filtered = [s for s in slots if weekday in s]  # assume weekday name appears in slot string
    elif slots and filter_type == "Առաջին հասանելի օրը":
        # Only keep the earliest slot (slots are presumed sorted by date/time)
        filtered = [slots[0]]

    # Format and send results
    if not filtered:
        await update.message.reply_text("Ներկայումս ազատ քննության ժամեր չկան։")
    else:
        result_text = "Հասանելի քննության ժամեր՝\n" + "\n".join(f"• {slot}" for slot in filtered)
        await update.message.reply_text(result_text)

# Command handler to cancel the conversation at any time
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allow the user to cancel the interaction."""
    await update.message.reply_text("Գործընթացը ընդհատվել է։ /start՝ սկսելու համար կրկին:")
    return ConversationHandler.END

if __name__ == "__main__":
    # Initialize application with token
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).concurrent_updates(False).build()
    # Build conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, handle_phone)],
            BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_branch)],
            EXAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exam_type)],
            FILTER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filter_type)],
            WEEKDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weekday)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    # Start polling Telegram for updates (runs until interrupted)
    application.run_polling()
