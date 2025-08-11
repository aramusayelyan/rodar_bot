import os
import logging
from datetime import datetime
from telegram import (Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
                      InlineKeyboardButton)
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from scraper import fetch_availability  # ֆունկցիա տվյալների քաղման համար (Selenium)

# Ստանալ Token և Admin chat ID միջավայրի փոփոխականներից (կամ սահմանել բեռնելով `.env` ֆայլից)
BOT_TOKEN = os.getenv("BOT_TOKEN", "<YOUR-BOT-TOKEN>")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # պետք է լրացնել ադմինի real chat ID-ն որպես փոփոխական

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Նախապատրաստել ներքին data structure՝ availability տվյալների համար
# context.bot_data['availability'] կպահի ստացված տվյալները ձևաչափով: availability[branch][exam_type] = { date: [times] }
# Օրինակ: availability["Yerevan"]["theory"] = { date_obj: ["09:00", "09:15", ...], ... }
# Այս structure-ն թարմացվելու է background task-ի կողմից:
# Նշում: Branch-երն այստեղ կարելի է պահել անգլերեն կամ հայերեն անվանումներով կամ ID-ներով:
# Մենք կպահենք branch-ի անգլերեն կարճ անուն (օր. "Yerevan") հարմարության համար, իսկ exam_type որպես "theory"/"practical".

# Հնարավոր է սահմանել global փոփոխական այս տվյալների համար, բայց կօգտագործենք context.bot_data dictionary-ը, 
# որը application-ի life-time հիշողության տեղն է:


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Սկիզբ command-ի handler - ուղարկել ողջույն և հարցնել contact"""
    user = update.effective_user
    # Start message
    welcome_text = (
        f"Բարի գալուստ, {user.first_name if user.first_name else 'օգտատեր'}!\n"
        "Խնդրում ենք սկսելու համար կիսվել Ձեր հեռախոսահամարով։ Սեղմեք ստորև բերված կոճակը։"
    )
    # Պատրաստել reply keyboard-ը request_contact կոճակով
    contact_button = KeyboardButton(text="📱 Կիսվել հեռախոսահամարով", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    # Ուղարկել ողջույնի հաղորդագրությունը contact կոճակով
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ստանալ օգտատիրոջ կոնտակտը (հեռախոսահամարը)"""
    contact = update.message.contact
    if contact is None:
        return  # Եթե ինչ-ինչ պատճառներով contact data չկա, դադարեցնել
    # Պահպանել օգտատիրոջ հեռախոսահամարը user_data-ում
    context.user_data["phone"] = contact.phone_number
    # Ողջունել և անցնել հիմնական ընտրացանկի
    await update.message.reply_text(
        "Շնորհակալություն։ Ձեր հեռախոսահամարը ստացվեց։\n"
        "Հիմա ընտրեք ստորաբաժանումը՝ որտեղ ցանկանում եք հանձնել քննությունը։",
        reply_markup=InlineKeyboardMarkup(generate_branch_buttons())
    )
    # Այստեղ մենք օգտագործում ենք InlineKeyboardMarkup հիմնական ընտրացանկի համար,
    # ուստի հեռացնում ենք contact request keyboard-ը (որը one_time_keyboard=True էր և արդեն անտեսանելի կլինի):

def generate_branch_buttons():
    """Պատրաստել ստորաբաժանման (քաղաքի) ընտրության կոճակները InlineKeyboard-ի համար"""
    # Նախապատրաստված ցանկ ստորաբաժանումների (ID: Անվանում կարճ)
    branches = [
        (1, "Երևան"), (2, "Գյումրի"), (3, "Վանաձոր"), (4, "Արմավիր"),
        (5, "Կոտայք"), (6, "Արտաշատ"), (7, "Աշտարակ"), (8, "Կապան"),
        (9, "Իջևան"), (10, "Սևան"), (11, "Մարտունի"), (12, "Գորիս"), (13, "Վայք")
    ]
    buttons = []
    for branch_id, name in branches:
        # Կառուցել callback data ձևաչափով `BR_<id>`
        buttons.append([InlineKeyboardButton(text=f"{branch_id}. {name}", callback_data=f"BR_{branch_id}")])
    # Ավելացնել "Հետադարձ կապ" կոճակը առանձին ստորոտում
    buttons.append([InlineKeyboardButton(text="📩 Հետադարձ կապ", callback_data="FB")])
    return buttons

async def branch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ստորաբաժանման ընտրության callback"""
    query = update.callback_query
    await query.answer()  # պատասխանել callback-ին որպեսզի Telegram-ը հեռացնի loading-ն
    data = query.data  # למשל "BR_1"
    # Ստանալ branch ID
    try:
        branch_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        return
    # Պահպանել օգտատիրոջ ընտրած branch ID-ը կամ անունը
    context.user_data["branch_id"] = branch_id
    # Կարող ենք նաև պահպանել branch անվանումը հեշտության համար (օր. "Երևան")
    branch_name = get_branch_name(branch_id)
    context.user_data["branch_name"] = branch_name
    # Հիմա առաջարկել ընտրել քննության տեսակը
    buttons = [
        [InlineKeyboardButton(text="Տեսական", callback_data="EX_theory")],
        [InlineKeyboardButton(text="Գործնական", callback_data="EX_practical")],
        [InlineKeyboardButton(text="🔙 Փոխել բաժին", callback_data="CHANGE_BRANCH")]
    ]
    # Վերանվերափոխել ուղերձը՝ առաջարկելով քննության տեսակը
    await query.edit_message_text(
        f"Ընտրած ստորաբաժանումը՝ {branch_name}։\nՀիմա ընտրեք քննության տեսակը․",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def get_branch_name(branch_id: int) -> str:
    """Օժանդակ ֆունկցիա՝ ID-ով ստանալու քաղաքի անվանումը"""
    branch_map = {
        1: "Երևան", 2: "Գյումրի", 3: "Վանաձոր", 4: "Արմավիր",
        5: "Կոտայք", 6: "Արտաշատ", 7: "Աշտարակ", 8: "Կապան",
        9: "Իջևան", 10: "Սևան", 11: "Մարտունի", 12: "Գորիս", 13: "Վայք"
    }
    return branch_map.get(branch_id, "անհայտ")

async def exam_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Քննության տեսակի ընտրության callback"""
    query = update.callback_query
    await query.answer()
    data = query.data  # "EX_theory" կամ "EX_practical"
    exam_type = "theory" if data == "EX_theory" else "practical"
    context.user_data["exam_type"] = exam_type
    # Առաջարկել ծառայության տարբերակները (ազատ օր, ըստ ամսաթվի, ըստ ժամի)
    buttons = [
        [InlineKeyboardButton(text="Առաջիկա ազատ օր", callback_data="SV_free")],
        [InlineKeyboardButton(text="Փնտրել ըստ ամսաթվի", callback_data="SV_date")],
        [InlineKeyboardButton(text="Փնտրել ըստ ժամի", callback_data="SV_time")],
        [InlineKeyboardButton(text="🔙 Վերադառնալ", callback_data="CHANGE_BRANCH")]  # թույլ տալ վերադառնալ բաժնի ընտրություն
    ]
    branch_name = context.user_data.get("branch_name", "ընտրրված բաժին")
    exam_text = "տեսական" if exam_type == "theory" else "գործնական"
    await query.edit_message_text(
        f"Ընտրած ստորաբաժանում՝ {branch_name}, {exam_text} քննություն։\n"
        "Խնդրում ենք ընտրելdesired ծառայությունը․",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ծառայության (որոնման տիպի) ընտրության callback"""
    query = update.callback_query
    await query.answer()
    service = query.data  # "SV_free", "SV_date" կամ "SV_time"
    branch_id = context.user_data.get("branch_id")
    exam_type = context.user_data.get("exam_type")
    branch_name = context.user_data.get("branch_name", "")
    if not branch_id or not exam_type:
        # Եթե ինչ-որ տվյալ չկա, դադարեցնել
        await query.edit_message_text("Խնդրում ենք նախ ընտրել ստորաբաժանումն ու քննության տեսակը։")
        return
    # Կախված ծառայության տեսակից՝ կամ անմիջապես արդյունք ցույց տալ, կամ հարցնել լրացուցիչ info (ամսաթիվ/ժամ)
    if service == "SV_free":
        # Առաջիկա ազատ օրվա և ժամի որոնում
        availability = context.bot_data.get("availability", {})
        result_text = "Ներկա պահին տվյալ բաժնի համար տվյալներ առկա չեն։"
        # Ստուգել availability-ում տվյալ branch/exam-ի info
        branch_key = branch_name  # մենք availability-ի մեջ պահում ենք branch անունով (անգլերեն կամ հայերեն)
        exam_key = exam_type  # "theory" կամ "practical"
        if branch_key in availability and exam_key in availability[branch_key]:
            slots_by_date = availability[branch_key][exam_key]  # սա dictionary է date -> [times]
            if slots_by_date:
                # Գտնել ամենափոքր (հունավազն) ամսաթիվը
                next_date = min(slots_by_date.keys())
                times = slots_by_date[next_date]
                if times:
                    next_time = min(times)  # վերցնել առավոտյան ամենավաղ ժամը
                    date_str = next_date.strftime("%d.%m.%Y")
                    result_text = f"Առաջիկա ազատ սլոթը՝ {date_str} - ժամը {next_time}։"
            else:
                result_text = "Ազատ սլոթեր फिलहाल հասանելի չեն այս բաժնի համար։"
        await query.edit_message_text(result_text)
        # Արդյունքը ցուցադրելուց հետո առաջարկել նոր որոնում կամ ավարտ
        await update.effective_chat.send_message(
            "🔎 Կատարել նո՞ր որոնում, թե ավարտել։",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="Նոր որոնում սկսել", callback_data="CHANGE_BRANCH")]
            ])
        )
    elif service == "SV_date":
        # Հարցնել օգտատիրոջը մուտքագրել ամսաթիվ
        context.user_data["expected"] = "date"
        # Պահպանել, որ սպասում ենք ամսաթիվ (որպես տեքստ)
        await query.edit_message_text("Խնդրում ենք մուտքագրել որոնվող ամսաթիվը՝ ձևաչափով ՕՕ.ԱԱԱԱ (օրինակ՝ 15.09.2025)։")
    elif service == "SV_time":
        context.user_data["expected"] = "time"
        await query.edit_message_text("Խնդրում ենք մուտքագրել որոնվող ժամը՝ ձևաչափով ԺԺ:ՐՐ (օրինակ՝ 09:30)։")
    elif service == "CHANGE_BRANCH":
        # Օգտատերը որոշել է վերադառնալ բաժնի ընտրության փուլ
        await query.edit_message_text(
            "Խնդրում ենք ընտրել ստորաբաժանումը․",
            reply_markup=InlineKeyboardMarkup(generate_branch_buttons())
        )
    else:
        # Անճանաչ ծառայություն
        await query.edit_message_text("Ընտրությունը չի ճանաչվում։")

async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Հետադարձ կապ կոճակի callback"""
    query = update.callback_query
    await query.answer()
    # Օգտատիրոջը ուղարկել հուշում՝ գրել հաղորդագրությունը
    await query.edit_message_text("Խնդրում ենք գրել Ձեր հաղորդագրությունը ադմինին ուղարկելու համար։")
    # Սահմանել state, որ սպասվում է feedback տեքստ
    context.user_data["expected"] = "feedback"

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message handler ընդունելու համար text input (feedback, date, time)"""
    user_text = update.message.text
    expected = context.user_data.get("expected")
    if not expected:
        # Եթե չկան ակնկալվող տվյալներ, գուցե օգտատերը ուղղակի գրել է ինչ-որ բան անտեղի
        # Տվյալ դեպքում պարզապես առաջարկենք օգտագործել /start կամ ընտրացանկ
        await update.message.reply_text("Խնդրում ենք ընտրել պահանջվող տարբերակը ընտրացանկից (/start).")
        return

    if expected == "feedback":
        # Օգտատիրոջ feedback հաղորդագրությունը առկա է user_text-ում
        # Պատրաստել admin-ին ուղարկվող հաղորդագրությունը
        user = update.effective_user
        phone = context.user_data.get("phone", "")
        admin_text = f"Feedback from {user.first_name} {user.last_name or ''} (phone: {phone}):\n{user_text}"
        if ADMIN_CHAT_ID:
            try:
                # Ուղարկել հաղորդագրությունը ադմինին
                await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=admin_text)
            except Exception as e:
                logger.error(f"Failed to send feedback to admin: {e}")
        # Հաստատել օգտատիրոջը
        await update.message.reply_text("Ձեր հաղորդագրությունն ուղարկվեց ադմինին։ Շնորհակալություն հետադարձ կապի համար։")
        # Մաքրել expected դրոշակը
        context.user_data["expected"] = None
        # Վերադառնալ գլխավոր ընտրացանկի (բաժնի ընտրության) փուլ
        await update.message.reply_text(
            "Վերադառնում ենք գլխավոր ընտրացանկ։ Ընտրեք ստորաբաժանումը․",
            reply_markup=InlineKeyboardMarkup(generate_branch_buttons())
        )
    elif expected == "date":
        # Օգտատերը ուղարկել է ամսաթիվ որոնման համար
        query_date_str = user_text.strip()
        # Փորձել վերափոխել date ձևաչափի
        try:
            # Ընդունում ենք ձևաչափը ՕՕ.ԱԱ.ՏՏՏՏ կամ ԱԱԱԱ-ԱԱ-ՕՕ
            if "." in query_date_str:
                query_date = datetime.strptime(query_date_str, "%d.%m.%Y").date()
            elif "-" in query_date_str:
                query_date = datetime.strptime(query_date_str, "%Y-%m-%d").date()
            else:
                raise ValueError("Unknown date format")
        except Exception as e:
            await update.message.reply_text("Ներմուծված ամսաթվի ձևաչափը սխալ է։ Խնդրում ենք փորձել կրկին՝ ՕՕ.ԱԱ.ՏՏՏՏ ձևաչափով։")
            return
        # Փնտրել տվյալ ամսաթվի հասանելի սլոթերը
        branch_name = context.user_data.get("branch_name", "")
        exam_type = context.user_data.get("exam_type", "")
        availability = context.bot_data.get("availability", {})
        result_text = ""
        branch_key = branch_name
        exam_key = exam_type
        if branch_key in availability and exam_key in availability[branch_key]:
            slots_by_date = availability[branch_key][exam_key]
            # Որոնել query_date-ը slots_by_date keys-ում
            if query_date in slots_by_date:
                times = slots_by_date[query_date]
                if times:
                    times_str = ", ".join(times)
                    date_str = query_date.strftime("%d.%m.%Y")
                    result_text = f"{date_str} օրն ազատ են հետևյալ ժամերը՝ {times_str}"
                else:
                    result_text = f"{query_date_str} օրն آزاد ժամեր հասանելի չեն։"
            else:
                result_text = f"{query_date_str} օրն տվյալ բաժնի համար ազատ ժամեր չկան։"
        else:
            result_text = "Տվյալները հասանելի չեն կամ տվյալ բաժնի/քննության համար հայտնի չէ։"
        await update.message.reply_text(result_text)
        # Մաքրել state-ը և առաջարկել նոր որոնում
        context.user_data["expected"] = None
        await update.message.reply_text(
            "🔎 Կարող եք կատարել նոր որոնում կամ փոխել բաժինը։",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="Նոր որոնում սկսել", callback_data="CHANGE_BRANCH")]
            ])
        )
    elif expected == "time":
        # Օգտատիրոջ ուղարկած ժամի մշակումը
        query_time_str = user_text.strip()
        # Validate ձևաչափ ԺԺ:ՐՐ
        try:
            query_time = datetime.strptime(query_time_str, "%H:%M").time()
        except Exception:
            await update.message.reply_text("Ժամը խնդրում ենք գրել ԺԺ:ՐՐ ձևաչափով (օրինակ՝ 07:30):")
            return
        # Որոնել այդ ժամով օրերը
        branch_name = context.user_data.get("branch_name", "")
        exam_type = context.user_data.get("exam_type", "")
        availability = context.bot_data.get("availability", {})
        branch_key = branch_name
        exam_key = exam_type
        found_dates = []
        if branch_key in availability and exam_key in availability[branch_key]:
            slots_by_date = availability[branch_key][exam_key]
            for date_obj, times in slots_by_date.items():
                # times ցուցակում ("HH:MM") գտնել query_time_str
                if query_time_str in times:
                    found_dates.append(date_obj)
        if found_dates:
            # Sort the dates
            found_dates.sort()
            dates_str = ", ".join([d.strftime("%d.%m.%Y") for d in found_dates])
            result_text = f"Ժամը {query_time_str}-ին հասանելի է հետևյալ օրերին՝ {dates_str}"
        else:
            result_text = f"Ժամը {query_time_str}-ին առաջիկայում ազատ օրեր չեն գտնվել։"
        await update.message.reply_text(result_text)
        context.user_data["expected"] = None
        await update.message.reply_text(
            "🔎 Կարող եք որոնել կրկին կամ ընտրել այլ բաժին․",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="Նոր որոնում սկսել", callback_data="CHANGE_BRANCH")]
            ])
        )
    else:
        # Ոչ մի очакված state-ին չհամապատասխանող տեքստ
        await update.message.reply_text("Չհաջողվեց մշակել հաղորդագրությունը։")

# Background task: Data refresh every 2 hours
async def refresh_data_job(context: ContextTypes.DEFAULT_TYPE):
    """Պարբերաբար կանչվող task՝ թարմացնելու համար availability տվյալները"""
    logger.info("Refreshing availability data from roadpolice.am...")
    try:
        new_data = fetch_availability()  # կանչել scraper.py-ի հիմնական ֆունկցիան
        # Թարմացնել ընդհանուր data-ը
        context.bot_data["availability"] = new_data
        logger.info("Availability data refreshed successfully.")
    except Exception as e:
        logger.error(f"Data refresh failed: {e}")

def main():
    # Ստեղծել Application (python-telegram-bot v20+)
    application = Application.builder().token(BOT_TOKEN).build()

    # Գրանցել handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    # CallbackQueryHandlers for branch, exam, service, feedback
    application.add_handler(CallbackQueryHandler(branch_callback, pattern=r"^BR_"))
    application.add_handler(CallbackQueryHandler(exam_callback, pattern=r"^EX_"))
    application.add_handler(CallbackQueryHandler(service_callback, pattern=r"^SV_|CHANGE_BRANCH"))
    application.add_handler(CallbackQueryHandler(feedback_callback, pattern=r"^FB$"))
    # Message handler for expected text inputs (date/time/feedback)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Սկսել background job for data refresh (every 2 hours)
    # First immediate run on startup to populate data
    application.job_queue.run_once(refresh_data_job, when=0)
    # Then run every 2 hours (7200 seconds)
    application.job_queue.run_repeating(refresh_data_job, interval=7200, first=7200)

    logger.info("Bot is starting...")
    # Զարգացնել polling-ը
    application.run_polling()

if __name__ == "__main__":
    main()
