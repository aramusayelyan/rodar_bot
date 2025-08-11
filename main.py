import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from config import TELEGRAM_TOKEN
from keyboards import (
    BRANCHES, branch_keyboard, exam_keyboard, filter_keyboard,
    weekday_keyboard, contact_request_keyboard, THEORY_ID, PRACTICE_ID
)
from scraper import fetch_available_slots

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("bot")

# Սթեյթներ
PHONE, BRANCH, EXAM, FILTER, WEEKDAY, DATE_INPUT, HOUR_INPUT = range(7)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Բարի գալուստ, {user.first_name or 'Օգտագործող'} 😊"
    )
    if context.user_data.get("phone"):
        await update.message.reply_text("Ձեր հեռախոսահամարը արդեն պահպանված է։")
        await update.message.reply_text("Ընտրեք բաժինը՝", reply_markup=branch_keyboard())
        return BRANCH
    else:
        await update.message.reply_text(
            "Խնդրում եմ կիսվել Ձեր հեռախոսահամարով՝ շարունակելու համար։",
            reply_markup=contact_request_keyboard
        )
        return PHONE

# Հեռախոսահամար
async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Սեղմեք «📱 Կիսվել հեռախոսահամարով» կոճակը։")
        return PHONE
    context.user_data["phone"] = contact.phone_number
    await update.message.reply_text("Շնորհակալություն, հեռախոսահամարը պահպանված է ✅")
    await update.message.reply_text("Ընտրեք բաժինը՝", reply_markup=branch_keyboard())
    return BRANCH

# Բաժին
async def branch_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        bid = int(q.data.split(":")[1])
    except Exception:
        await q.edit_message_text("Սխալ ընտրություն։ Փորձեք նորից /start")
        return ConversationHandler.END
    context.user_data["branch_id"] = bid
    name = next((n for n, id_ in BRANCHES if id_ == bid), "Ընտրված բաժին")
    await q.edit_message_text(f"Ընտրված բաժինը՝ {name} 🏢")
    await q.message.reply_text("Ընտրեք քննության տեսակը՝", reply_markup=exam_keyboard())
    return EXAM

# Քննության տեսակ
async def exam_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        sid = int(q.data.split(":")[1])
    except Exception:
        await q.edit_message_text("Սխալ քննության տեսակ։ Սկսեք /start")
        return ConversationHandler.END
    context.user_data["service_id"] = sid
    await q.edit_message_text(
        f"Ընտրված՝ {'Տեսական' if sid == THEORY_ID else 'Գործնական'} քննություն 📝"
    )
    await q.message.reply_text("Ընտրեք ֆիլտրի տարբերակը՝", reply_markup=filter_keyboard())
    return FILTER

# Ֆիլտր
async def filter_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data.split(":")[1]
    context.user_data["filter"] = choice
    if choice == "weekday":
        await q.edit_message_text("Ընտրեք շաբաթվա օրը՝", reply_markup=weekday_keyboard())
        return WEEKDAY
    elif choice == "date":
        await q.edit_message_text("Մուտքագրեք ամսաթիվը՝ ՕՕ.ԱԱ.ՏՏՏՏ ձևաչափով (օր․ 05.09.2025)")
        return DATE_INPUT
    elif choice == "hour":
        await q.edit_message_text("Մ
