import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from config import TELEGRAM_TOKEN
from keyboards import BRANCH_OPTIONS, EXAM_TYPE_OPTIONS, FILTER_TYPE_OPTIONS, WEEKDAY_OPTIONS
from scraper import fetch_available_slots

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PHONE, BRANCH, EXAM_TYPE, FILTER_TYPE, WEEKDAY = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    btn = KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)
    kb = ReplyKeyboardMarkup([[btn]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Բարի գալուստ։ Խնդրում եմ ուղարկեք Ձեր հեռախոսահամարը կամ սեղմեք կոճակը։",
        reply_markup=kb,
    )
    return PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data["phone"] = phone.strip()
    branches_rows = [BRANCH_OPTIONS[i:i+3] for i in range(0, len(BRANCH_OPTIONS), 3)]
    await update.message.reply_text(
        "Ընտրեք հաշվառման-քննական բաժինը․",
        reply_markup=ReplyKeyboardMarkup(branches_rows, one_time_keyboard=True, resize_keyboard=True),
    )
    return BRANCH

async def receive_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["branch"] = update.message.text
    await update.message.reply_text(
        "Ընտրեք քննության տեսակը․",
        reply_markup=ReplyKeyboardMarkup([EXAM_TYPE_OPTIONS], one_time_keyboard=True, resize_keyboard=True),
    )
    return EXAM_TYPE

async def receive_exam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["exam_type"] = update.message.text
    await update.message.reply_text(
        "Ինչպես ցուցադրել արդյունքները։",
        reply_markup=ReplyKeyboardMarkup([FILTER_TYPE_OPTIONS], one_time_keyboard=True, resize_keyboard=True),
    )
    return FILTER_TYPE

async def receive_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    context.user_data["filter_type"] = choice
    if choice == "Ըստ շաբաթվա օրվա":
        rows = [WEEKDAY_OPTIONS[:3], WEEKDAY_OPTIONS[3:6], WEEKDAY_OPTIONS[6:]]
        await update.message.reply_text(
            "Ընտրեք շաբաթվա օրը․",
            reply_markup=ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True),
        )
        return WEEKDAY
    await provide_results(update, context)
    return ConversationHandler.END

async def receive_weekday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["weekday"] = update.message.text
    await provide_results(update, context)
    return ConversationHandler.END

async def provide_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    branch = context.user_data.get("branch")
    exam_type = context.user_data.get("exam_type")
    filter_type = context.user_data.get("filter_type")
    weekday = context.user_data.get("weekday")

    await update.message.reply_text("🔎 Փնտրում ենք հասանելի ժամեր, խնդրում ենք սպասել…")
    slots = await asyncio.to_thread(fetch_available_slots, branch, exam_type)

    if slots is None:
        await update.message.reply_text("Ներողություն, տվյալները ստանալ չհաջողվեց։ Փորձեք մի փոքր ուշ։")
        return

    filtered = slots
    if filter_type == "Ըստ շաբաթվա օրվա":
        filtered = [s for s in slots if weekday and weekday in s]
    elif filter_type == "Առաջին հասանելի օրը" and slots:
        filtered = [slots[0]]

    if not filtered:
        await update.message.reply_text("Այս պահին ազատ ժամեր չեն գտնվել։")
    else:
        await update.message.reply_text("Հասանելի ժամեր՝\n" + "\n".join(f"• {s}" for s in filtered))

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Գործընթացը չեղարկվեց։ /start՝ նորից սկսելու համար։")
    return ConversationHandler.END

def main() -> None:
    app: Application = ApplicationBuilder().token(TELEGRAM_TOKEN).concurrent_updates(False).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), receive_phone)],
            BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_branch)],
            EXAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_exam)],
            FILTER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter)],
            WEEKDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_weekday)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
