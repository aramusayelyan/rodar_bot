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
        await q.edit_message_text("Մուտքագրեք ժամը (0-23)՝ օրինակ 9 կամ 15")
        return HOUR_INPUT
    elif choice == "all":
        await q.edit_message_text("Ստուգում եմ բոլոր առկա օրերը․․․")
        return await fetch_and_send(update, context)
    else:
        await q.edit_message_text("Անհայտ ընտրություն։ /start")
        return ConversationHandler.END

# Շաբաթվա օր
async def weekday_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        idx = int(q.data.split(":")[1])
    except Exception:
        await q.edit_message_text("Սխալ շաբաթվա օր։")
        return ConversationHandler.END
    context.user_data["weekday_index"] = idx
    await q.edit_message_text("Ստուգում եմ ընտրված օրվա ազատ ժամերը․․․")
    return await fetch_and_send(update, context)

# Ամսաթիվ
async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().replace("/", ".")
    try:
        d, m, y = map(int, text.split("."))
        qd = datetime(y, m, d).date()
    except Exception:
        await update.message.reply_text("Խնդրում եմ գրեք ճիշտ՝ ՕՕ.ԱԱ.ՏՏՏՏ (օր․ 05.09.2025)")
        return DATE_INPUT
    context.user_data["query_date"] = qd
    await update.message.reply_text("Ստուգում եմ ընտրված ամսաթվի ազատ ժամերը․․․")
    return await fetch_and_send(update, context)

# Ժամ
async def hour_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text.isdigit():
        await update.message.reply_text("Մուտքագրեք ժամը՝ թվով (0-23)")
        return HOUR_INPUT
    hr = int(text)
    if hr < 0 or hr > 23:
        await update.message.reply_text("Ժամը պետք է լինի 0-ից 23։")
        return HOUR_INPUT
    context.user_data["hour"] = hr
    await update.message.reply_text("Ստուգում եմ ընտրված ժամի ազատ ժամերը․․․")
    return await fetch_and_send(update, context)

# Սլոթերի քաշում և ուղարկում
async def fetch_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bid = context.user_data.get("branch_id")
    sid = context.user_data.get("service_id")
    if not bid or not sid:
        if update.callback_query:
            await update.callback_query.edit_message_text("Տեղի ունեցավ սխալ։ Սկսեք /start")
        else:
            await update.message.reply_text("Տեղի ունեցավ սխալ։ Սկսեք /start")
        return ConversationHandler.END

    filt = context.user_data.get("filter")
    f_weekday = context.user_data.get("weekday_index")
    f_date = context.user_data.get("query_date")
    f_hour = context.user_data.get("hour")

    slots = fetch_available_slots(
        branch_id=bid,
        service_id=sid,
        filter_weekday=f_weekday,
        filter_date=f_date,
        filter_hour=f_hour
    )

    branch_name = next((n for n, id_ in BRANCHES if id_ == bid), "Ընտրված բաժին")
    exam_name = "տեսական" if sid == THEORY_ID else "գործնական"

    if not slots:
        msg = f"Ցավոք, {branch_name} բաժնում «{exam_name}» քննության համար այս պահի դրությամբ ազատ օր/ժամ չկա։"
    else:
        lines = [f"Ազատ օր/ժամեր {branch_name} բաժնում («{exam_name}»):"]
        for d, t in slots[:120]:  # սահմանափակենք չափը
            mname = MONTHS_HY[d.month-1] if 1 <= d.month <= 12 else f"{d.month}-րդ ամիս"
            lines.append(f"• {d.day} {mname} {d.year} — {t}")
        msg = "\n".join(lines)

    if update.callback_query:
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)
    return ConversationHandler.END

# /slots — արագ ստուգում վերջին ընտրված պարամետրերով
async def quick_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (context.user_data.get("branch_id") and context.user_data.get("service_id")):
        await update.message.reply_text("Նախ կատարեք ընտրությունները՝ /start")
        return
    await update.message.reply_text("Ստուգում եմ վերջին պահպանված ընտրություններով․․․")
    # reset filter to 'all'
    context.user_data.pop("weekday_index", None)
    context.user_data.pop("query_date", None)
    context.user_data.pop("hour", None)
    context.user_data["filter"] = "all"
    await fetch_and_send(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Գործողությունը չեղարկվեց։")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, phone_received)],
            BRANCH: [CallbackQueryHandler(branch_chosen, pattern=r"^branch:\d+$")],
            EXAM: [CallbackQueryHandler(exam_chosen, pattern=r"^exam:\d+$")],
            FILTER: [CallbackQueryHandler(filter_chosen, pattern=r"^filter:(weekday|date|hour|all)$")],
            WEEKDAY: [CallbackQueryHandler(weekday_selected, pattern=r"^weekday:\d$")],
            DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_entered)],
            HOUR_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hour_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("slots", quick_slots))

    logger.info("Bot is polling…")
    app.run_polling()

if __name__ == "__main__":
    main()
