import os
import logging
from telegram import (
    ReplyKeyboardMarkup, KeyboardButton, Update
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, JobQueue
)
from config import BOT_TOKEN
from keyboards import main_menu_keyboard, exam_type_keyboard, service_keyboard
from scraper import fetch_availability  # Selenium scraper that gets real data

# Initialize logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory user session storage and availability cache
user_data = {}
availability_cache = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("📱 Ուղարկել հեռախոսահամար", request_contact=True)
    await update.message.reply_text(
        "Բարև 👋\nԽնդրում եմ կիսվեք ձեր հեռախոսահամարով՝ շարունակելու համար:",
        reply_markup=ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    )

async def save_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        return
    chat_id = update.message.chat_id
    user_data[chat_id] = {"phone": contact.phone_number}
    await update.message.reply_text(
        "✅ Հեռախոսահամարը ստացվեց։\nԸնտրեք ստորաբաժանումը՝",
        reply_markup=main_menu_keyboard()
    )

async def handle_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in user_data:
        await update.message.reply_text("Խնդրում եմ սկսեք /start հրամանով։")
        return
    dept = update.message.text
    user_data[chat_id]["department"] = dept
    await update.message.reply_text("Ընտրեք քննության տեսակը:", reply_markup=exam_type_keyboard())

async def handle_exam_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in user_data or "department" not in user_data[chat_id]:
        await update.message.reply_text("Խնդրում եմ նախ ընտրեք ստորաբաժանումը։")
        return
    exam_type = update.message.text
    user_data[chat_id]["exam_type"] = exam_type
    await update.message.reply_text("Ընտրեք որոնման տեսակն՝", reply_markup=service_keyboard())

async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in user_data or "department" not in user_data[chat_id] or "exam_type" not in user_data[chat_id]:
        await update.message.reply_text("Խնդրում եմ նախ սահմանեք բոլոր նախնական ընտրությունները։")
        return
    service = update.message.text
    dept = user_data[chat_id]["department"]
    exam = user_data[chat_id]["exam_type"]

    # Use cached availability data
    data = availability_cache.get(dept, {}).get(exam, {})

    response = []
    if service == "Առաջիկա ազատ օր":
        # Find the earliest date and time
        if data:
            earliest_date = min(data.keys())
            earliest_time = min(data[earliest_date])
            response.append(f"Առաջիկա ազատ slot\n{earliest_date} - {earliest_time}")
        else:
            response.append("Ներեցեք, առայժմ տվյալներ չկան։")
    elif service == "Ըստ ամսաթվի":
        await update.message.reply_text("Խնդրում եմ մուտքագրեք արտահայտ օրվա (օր.՝ 15.09.2025):")
        context.user_data[chat_id] = {"service": "date_search", "dept": dept, "exam": exam}
        return
    elif service == "Ըստ ժամի":
        await update.message.reply_text("Խնդրում եմ մուտքագրեք ո՞ր ժամը եք ուզում (օր.՝ 09:30):")
        context.user_data[chat_id] = {"service": "time_search", "dept": dept, "exam": exam}
        return
    else:
        response.append("Չհաջողվեց ճանաչել ծառայությունը։")

    await update.message.reply_text("\n".join(response))

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    ctx = context.user_data.get(chat_id, {})
    service = ctx.get("service")
    dept = ctx.get("dept")
    exam = ctx.get("exam")
    text = update.message.text

    data = availability_cache.get(dept, {}).get(exam, {})

    if service == "date_search":
        try:
            import datetime
            query_date = datetime.datetime.strptime(text.strip(), "%d.%m.%Y").date()
            times = data.get(query_date, [])
            if times:
                await update.message.reply_text(f"{query_date.strftime('%d.%m.%Y')} – ազատ ժամեր՝ {', '.join(times)}")
            else:
                await update.message.reply_text("Նշված օրը ազատ slot-եր չկան։")
        except Exception:
            await update.message.reply_text("Սխալ ձևաչափ։ Փորձեք ՕՕ.ԱԱԱԱ (օր.՝ 15.09.2025)")
    elif service == "time_search":
        matches = []
        for d, times_list in data.items():
            if text.strip() in times_list:
                matches.append(d.strftime("%d.%m.%Y"))
        if matches:
            await update.message.reply_text(f"{text} ժամին ազատ է ` {', '.join(matches)}")
        else:
            await update.message.reply_text(f"{text} ժամին ազատ slot-եր չկան առաջիկայում։")
    else:
        await update.message.reply_text("Խնդրում եմ կատարեք /start֊ը՝ կրկին սկսելուն։")

async def refresh_data(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Նոր տվյալների քաղում է roadpolice.am-ից...")
    data = fetch_availability()
    if data:
        global availability_cache
        availability_cache = data
        logger.info("Տվյալները թարմացվել են։")
    else:
        logger.error("Տվյալների քաղումն չհաջողվեց։")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    jq = app.job_queue
    jq.run_repeating(refresh_data, interval=2 * 3600, first=0)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, save_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_department))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exam_type))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    logger.info("Բոտը սկսել է աշխատել։")
    app.run_polling()

if __name__ == "__main__":
    main()
