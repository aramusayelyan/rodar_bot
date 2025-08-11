import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scraper import get_free_dates

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("📱 Տրամադրել հեռախոսահամար", request_contact=True)]]
    await update.message.reply_text("Բարև, խնդրում եմ տրամադրել Ձեր հեռախոսահամարը։", 
                                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    user_data_store[update.effective_user.id] = {"phone": phone}

    branches = [("Երևան", "branch_yerevan"), ("Գյումրի", "branch_gyumri")]
    kb = [[InlineKeyboardButton(text=b[0], callback_data=f"BR_{b[1]}")] for b in branches]
    await update.message.reply_text("Ընտրեք բաժինը․", reply_markup=InlineKeyboardMarkup(kb))

async def branch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    branch = update.callback_query.data.replace("BR_", "")
    user_data_store[update.effective_user.id]["branch"] = branch

    services = [
        ("Ազատ օրերի որոնում", "SV_free_days"),
        ("Ազատ օրերը ըստ ամսաթվի", "SV_by_date"),
        ("Ազատ օրերը ըստ ժամերի", "SV_by_time")
    ]
    kb = [[InlineKeyboardButton(s[0], callback_data=s[1])] for s in services]
    await update.callback_query.message.reply_text("Ընտրեք ծառայությունը․", reply_markup=InlineKeyboardMarkup(kb))

async def service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.callback_query.data
    user_data_store[update.effective_user.id]["service"] = service

    exams = [("Թեսթ", "EX_theory"), ("Գործնական", "EX_practical")]
    kb = [[InlineKeyboardButton(e[0], callback_data=e[1])] for e in exams]
    await update.callback_query.message.reply_text("Ընտրեք քնության տեսակը․", reply_markup=InlineKeyboardMarkup(kb))

async def exam_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exam = update.callback_query.data
    user_data_store[update.effective_user.id]["exam"] = exam

    branch = user_data_store[update.effective_user.id]["branch"]
    exam_type = "theory" if "theory" in exam else "practical"

    days = get_free_dates(branch_id=branch, exam_type=exam_type)
    if days:
        text = "📅 Ազատ օրեր․\n" + "\n".join(days)
    else:
        text = "🚫 Ազատ օրեր չկան։"
    await update.callback_query.message.reply_text(text)

async def refresh_data():
    print("♻ Ազատ օրերի տվյալները թարմացվում են...")

def build_app():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(CallbackQueryHandler(branch_callback, pattern=r"^BR_"))
    app.add_handler(CallbackQueryHandler(service_callback, pattern=r"^SV_"))
    app.add_handler(CallbackQueryHandler(exam_callback, pattern=r"^EX_"))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_data, "interval", hours=2)
    scheduler.start()

    return app

if __name__ == "__main__":
    application = build_app()
    application.run_polling()
