import os
import re
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# տեղական մոդուլներ
import scraper
import keyboards
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
SELECT_PHONE, ENTER_CODE, SELECT_DEPT, SELECT_EXAM, SELECT_SEARCH, ENTER_INFO = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler: greet user and ask for phone number (allow sharing contact)."""
    user = update.effective_user
    # Greeting message
    await update.message.reply_text(
        f"Բարեւ՛ {user.first_name if user.first_name else 'օգտագործող'}։\n"
        "Այս բոտի օգնությամբ Դուք կարող եք հերթագրվել Ճանապարհային ոստիկանությունում վարորդական քննության համար։\n"
        "Խնդրում եմ ուղարկել Ձեր հեռախոսահամարը (կամ սեղմել կոճակը՝ համարով կիսվելու համար)։\n\n"
        "Գործողությունից դուրս գալու համար ուղարկեք /cancel հարզանիշը։",
        reply_markup=keyboards.phone_request_keyboard()
    )
    return SELECT_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input (either as shared contact or text). Initiate login via Selenium (send SMS code)."""
    if update.message.contact:
        # If user shared contact
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
    # Keep only digits, remove '+' and spaces
    phone_digits = re.sub(r"\D", "", phone)
    # Remove country code if present (assume +374 for Armenia)
    if phone_digits.startswith("374"):
        phone_digits = phone_digits[3:]
    logger.info(f"Received phone: {phone_digits}")
    # Initiate Selenium: open site and send SMS code
    try:
        driver = await asyncio.get_running_loop().run_in_executor(
            None, scraper.login_start, phone_digits
        )
    except Exception as e:
        logger.error(f"Selenium login_start error: {e}")
        await update.message.reply_text("Խնդրում ենք क्षմել, խնդիր առաջացավ բոտի աշխատանքում։ Փորձեք կրկին։")
        return ConversationHandler.END
    # Store the Selenium WebDriver instance for later steps
    context.user_data["driver"] = driver
    # Ask for OTP code
    await update.message.reply_text("Խնդրում ենք մուտքագրել SMS-ով ստացած հաստատման կոդը։")
    return ENTER_CODE

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle SMS code input. Verify login and proceed to department selection."""
    code = update.message.text.strip()
    driver = context.user_data.get("driver")
    if not driver:
        await update.message.reply_text("Ներողություն, տեխնիկական խնդիր առաջացավ։ Փորձեք սկսելուց /start։")
        return ConversationHandler.END
    # Verify OTP code via Selenium
    try:
        success = await asyncio.get_running_loop().run_in_executor(
            None, scraper.login_verify, driver, code
        )
    except Exception as e:
        logger.error(f"Selenium login_verify error: {e}")
        await update.message.reply_text("Կայքից տվյալներ վերցնելու ընթացքում սխալ տեղի ունեցավ։ Փորձեք նորից /start հրամանով։")
        # Cleanup driver
        driver.quit()
        return ConversationHandler.END
    if not success:
        # Wrong code, ask again
        await update.message.reply_text("Մուտքագրած կոդը սխալ է։ Խնդրում ենք փորձել կրկին․")
        return ENTER_CODE
    # If login successful, retrieve list of departments
    try:
        dept_list = scraper.get_departments(driver)
    except Exception as e:
        logger.error(f"Error fetching departments: {e}")
        await update.message.reply_text("Չհաջողվեց ստանալ բաժինների ցանկը։ Փորձեք կրկին /start սկսել։")
        driver.quit()
        return ConversationHandler.END
    # Ask user to choose department (inline keyboard)
    await update.message.reply_text(
        "Ընտրեք հաշվառման-քննական բաժինը․",
        reply_markup=keyboards.department_keyboard(dept_list)
    )
    return SELECT_DEPT

async def choose_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle department selection via inline button."""
    query = update.callback_query
    await query.answer()  # acknowledge callback
    data = query.data  # e.g. "dept:123"
    if not data.startswith("dept:"):
        return SELECT_DEPT  # ignore unexpected data
    dept_value = data.split(":", 1)[1]
    dept_name = next((name for name, val in context.user_data.get("departments_list", []) if val == dept_value), None)
    context.user_data["department"] = dept_value
    context.user_data["department_name"] = dept_name
    # Ask for exam type
    await query.edit_message_text(
        text=f"Ընտրված բաժին՝ {dept_name}։\nԽնդրում ենք ընտրել քննության տեսակը․",
        reply_markup=keyboards.exam_type_keyboard()
    )
    return SELECT_EXAM

async def choose_exam_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle exam type selection via inline button."""
    query = update.callback_query
    await query.answer()
    exam_type = query.data  # "theoretical" or "practical"
    if exam_type not in ("theoretical", "practical"):
        return SELECT_EXAM
    context.user_data["exam_type"] = exam_type
    # Human-readable exam name for user feedback
    exam_label = "Տեսական" if exam_type == "theoretical" else "Գործնական"
    # Ask for search method
    await query.edit_message_text(
        text=f"Ընտրված քննության տեսակ՝ {exam_label}։\nԸնտրեք որոնման ձևը (օր, ամսաթիվ կամ ժամ)․",
        reply_markup=keyboards.search_method_keyboard()
    )
    return SELECT_SEARCH

async def choose_search_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search method (day/date/time) selection via inline button."""
    query = update.callback_query
    await query.answer()
    method = query.data  # "day", "date", or "time"
    if method not in ("day", "date", "time"):
        return SELECT_SEARCH
    context.user_data["search_mode"] = method
    if method == "day":
        # Search for earliest available slot (no additional input needed)
        await query.edit_message_text("🔄 Խնդրում ենք սպասել, կատարվում է որոնում...")
        driver = context.user_data.get("driver")
        branch_val = context.user_data.get("department")
        exam_type = context.user_data.get("exam_type")
        try:
            result_text = await asyncio.get_running_loop().run_in_executor(
                None, scraper.search_slots, driver, branch_val, exam_type, "day", None
            )
        except Exception as e:
            logger.error(f"Error searching slots: {e}")
            result_text = "Ներողություն, որոնումը ձախողվեց։ Փորձեք կրկին։"
        # Send the result to user
        await query.edit_message_text(result_text)
        # Cleanup Selenium driver
        if driver:
            driver.quit()
        return ConversationHandler.END
    elif method == "date":
        # Ask user to input a specific date
        await query.edit_message_text("Խնդրում ենք մուտքագրել Ձեր ուզած ամսաթիվը (օր․ 25.08.2025):")
        return ENTER_INFO
    elif method == "time":
        await query.edit_message_text("Խնդրում ենք մուտքագրել նախընտրած ժամը (օրինակ՝ 09:30):")
        return ENTER_INFO

async def receive_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user input for date or time search."""
    user_input = update.message.text.strip()
    mode = context.user_data.get("search_mode")
    driver = context.user_data.get("driver")
    branch_val = context.user_data.get("department")
    exam_type = context.user_data.get("exam_type")
    if mode == "date":
        # Validate date format (expect DD.MM.YYYY)
        if not re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}$", user_input):
            await update.message.reply_text("Խնդրում ենք մուտքագրել ամսաթիվը ձեւաչափով ՕՕ.АԱ.АԱԱԱ (օրինակ՝ 05.09.2025):")
            return ENTER_INFO
        search_value = user_input
    elif mode == "time":
        # Validate time format (expect HH:MM)
        if not re.match(r"^\d{1,2}:\d{2}$", user_input):
            await update.message.reply_text("Խնդրում ենք գրել ժամը ֆորմատով ԺԺ:ՐՐ (օրինակ՝ 09:30):")
            return ENTER_INFO
        search_value = user_input
    else:
        # Unexpected mode
        await update.message.reply_text("Տեղի է ունեցել սխալ։ Փորձեք նորից /start սկսել։")
        if driver:
            driver.quit()
        return ConversationHandler.END
    # Notify user of search start (typing action)
    await update.message.reply_text("⏳ Փնտրում ենք հասանելի տվյալներ, խնդրում ենք սպասել...")
    # Perform the search in background thread
    try:
        result_text = await asyncio.get_running_loop().run_in_executor(
            None, scraper.search_slots, driver, branch_val, exam_type, mode, search_value
        )
    except Exception as e:
        logger.error(f"Error searching slots ({mode}={search_value}): {e}")
        result_text = "Ներողություն, որոնումը չհաջողվեց։ Փորձեք կրկին։"
    # Send the result
    await update.message.reply_text(result_text)
    # Cleanup driver
    if driver:
        driver.quit()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Գործողությունը չեղարկված է։ Բարի օր մաղթեք!")
    # Cleanup if driver exists
    driver = context.user_data.get("driver")
    if driver:
        driver.quit()
    return ConversationHandler.END

def main() -> None:
    # Initialize bot application
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    # Set up conversation handler with the defined states and handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, receive_phone)],
            ENTER_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)],
            SELECT_DEPT: [CallbackQueryHandler(choose_department, pattern="^dept:")],
            SELECT_EXAM: [CallbackQueryHandler(choose_exam_type, pattern="^(theoretical|practical)$")],
            SELECT_SEARCH: [CallbackQueryHandler(choose_search_method, pattern="^(day|date|time)$")],
            ENTER_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_search_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    # Start polling the Telegram API
    app.run_polling()
    
if __name__ == "__main__":
    main()
