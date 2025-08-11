from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN
from keyboards import main_menu_keyboard, exam_type_keyboard, service_keyboard
from scraper import get_available_dates

user_data = {}

# /start հրաման
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("📱 Ուղարկել հեռախոսահամար", request_contact=True)
    await update.message.reply_text(
        "Բարև 🙌\nՈւղարկեք ձեր հեռախոսահամարը՝ շարունակելու համար։",
        reply_markup=ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)
    )

# Հեռախոսահամարի պահպանում
async def save_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.message.chat_id] = {"phone": update.message.contact.phone_number}
    await update.message.reply_text(
        "✅ Հեռախոսահամարը պահպանվեց։\nԸնտրեք ստորաբաժանումը։",
        reply_markup=main_menu_keyboard()
    )

# Սուբդիվիզիայի ընտրություն
async def choose_exam_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.message.chat_id]["department"] = update.message.text
    await update.message.reply_text("Ընտրեք քննության տեսակը։", reply_markup=exam_type_keyboard())

# Քննության տեսակի ընտրություն
async def choose_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.message.chat_id]["exam_type"] = update.message.text
    await update.message.reply_text("Ընտրեք ծառայությունը։", reply_markup=service_keyboard())

# Վերջնական արդյունքների ցուցադրում
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.message.text
    phone = user_data[update.message.chat_id]["phone"]
    department = user_data[update.message.chat_id]["department"]
    exam_type = user_data[update.message.chat_id]["exam_type"]

    results = get_available_dates(department, exam_type, service)
    if results:
        await update.message.reply_text("📅 Ազատ օրեր և ժամեր՝\n" + "\n".join(results))
    else:
        await update.message.reply_text("❌ Ազատ օրեր չեն գտնվել։")

# Ֆոնային թարմացման ֆունկցիա
async def refresh_data_job(context: ContextTypes.DEFAULT_TYPE):
    print("🔄 Տվյալների թարմացում...")  
    # Այստեղ կանչիր scraper ֆունկցիան, եթե ուզում ես նախապես քաշել տվյալները

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Job queue every 2 hours
    job_queue = application.job_queue
    job_queue.run_repeating(refresh_data_job, interval=2*60*60, first=0)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, save_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_exam_type))

    application.run_polling()

if __name__ == "__main__":
    main()
