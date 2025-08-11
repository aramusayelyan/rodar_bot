import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters
import config
import keyboards
from scraper import get_free_slots

# Սահմանել logger-ը
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Սահմանել conversation-ի վիճակների կոնստանտները
ASK_PHONE, ASK_BRANCH, ASK_EXAM = range(3)

# Start command-ի handler
async def start(update: Update, context):
    """ /start սկսելուց ուղարկել ողջույն և հարցնել հեռախոսահամար """
    user = update.effective_user
    await update.message.reply_text(
        f"Բարի գալուստ, {user.first_name}։\n"
        "Այս բոտը կօգնի Ձեզ պարզել վարորդական քննության հերթագրման ազատ օրերը և ժամերը։\n"
        "Խնդրում եմ սեղմեք ստորև բերված կոճակը՝ Ձեր հեռախոսահամարը տրամադրելու համար։"
    )
    # Ուղարկել կոճակ՝ հեռախոսահամար ստանալու համար
    await update.message.reply_text(
        "⬇️ Հեռախոսահամար փոխանցելու համար սեղմեք կոճակը",
        reply_markup=keyboards.phone_request_keyboard()
    )
    return ASK_PHONE

# Հեռախոսահամարի ստացման handler
async def phone_received(update: Update, context):
    """Ստանալ contact կամ վահանակով մուտքագրված հեռախոսահամար"""
    contact = update.message.contact
    if contact:
        phone_number = contact.phone_number
    else:
        # Եթե օգտատերը գրառեց որպես տեքստ (ոչ թե share contact), վերցնենք տեքստը
        phone_number = update.message.text
    # Հեռախոսահամարը կարող ենք պահել context.user_data dict-ում, եթե հետագայում օգտագործվի
    context.user_data["phone"] = phone_number
    logger.info("User phone: %s", phone_number)
    # Հիմա անցնում ենք հաջորդ քայլին՝ ստորաբաժանման ընտրություն
    await update.message.reply_text(
        "Շատ լավ, շնորհակալություն։ Հիմա ընտրեք մոտակա հաշվառման-քննական բաժանմունքը՝ որտեղ ցանկանում եք հանձնել քննությունը։",
        reply_markup=keyboards.branch_keyboard()
    )
    return ASK_BRANCH

# Ստորաբաժանման ընտրության handler
async def branch_received(update: Update, context):
    """Ընդունում է բաժանմունքի անունը (որպես տեքստ, կոճակից)"""
    branch = update.message.text
    context.user_data["branch"] = branch
    logger.info("User selected branch: %s", branch)
    # Հարցնել քննության/ծառայության տեսակը
    await update.message.reply_text(
        f"Ընտրեցիք՝ {branch}։ Հիմա ընտրեք քննության տեսակը կամ ծառայության видը։",
        reply_markup=keyboards.exam_type_keyboard()
    )
    return ASK_EXAM

# Քննության/ծառայության տեսակի ստացման handler
async def exam_received(update: Update, context):
    """Ընդունել քննության տեսակը և կանչել scraper ֆունկցիան, հետո արդյունքը ուղարկել"""
    exam = update.message.text
    branch = context.user_data.get("branch")
    phone = context.user_data.get("phone")
    logger.info("User selected exam type: %s", exam)

    # Տեղեկացնել օգտատիրոջը, որ տվյալները բերվում են (որոշ դեպքերում կարող է մի քանի վայրկյան տևել)
    await update.message.reply_text("Խնդրում եմ սպասեք, հավաքում եմ տվյալները ⏳...")

    # Կանչել scraper-ը տվյալ պարամետրերով
    try:
        slots = get_free_slots(branch, exam)
    except Exception as e:
        logger.error("Scraper error: %s", e, exc_info=True)
        await update.message.reply_text("Կներեք, սխալ առաջացավ տվյալներ հավաքելիս։ Խնդրում ենք փորձել ևս一次 ուշ։")
        return ConversationHandler.END

    # Վերամշակել արդյունքները և պատրաստել պատասխան msg
    if not slots or len(slots) == 0:
        # Ոչ մի ազատ օր չի գտնվել
        reply_text = (f"Ցավոք, {branch} բաժանմունքում «{exam}» համար ազատ օրեր ներկայումս չկան։
Լրացուցիչ տեղեկատվության համար կարող եք փորձել մեկ այլ բաժանմունք կամ稍后 կրկին ստուգել։")
    else:
        reply_lines = []
        for date_str, times in slots:
            # date_str հավանաբար YYYY-MM-DD ձևաչափով է, այն փոքր-ինչ ձևաչափենք ավելի ընթեռնելի համար։
            pretty_date = date_str
            try:
                # Փորձել ամսաթիվը ձևափոխել "DD.MM.YYYY" կամ "DD Month YYYY" ձևաչափի
                from datetime import datetime
                dt = datetime.fromisoformat(date_str)
                pretty_date = dt.strftime("%d.%m.%Y")
            except:
                pass
            if times:
                times_str = " | ".join(times)
                reply_lines.append(f"📅 {pretty_date} – առկա ժամեր: {times_str}")
            else:
                # Եթե times list դատարկ է, նշանակել "ժամը պարզ չէ"
                reply_lines.append(f"📅 {pretty_date} – հասանելի ժամ անորոշ")
        reply_text = (f"🔎 `{branch}` բաժանմունքում **{exam}** համար գտնվել է հետևյալ ազատ ժամանակացույցը.\n"
                      + "\n".join(reply_lines))
    # Ուղարկել օգտատիրոջը արդյունքը
    await update.message.reply_text(reply_text, parse_mode="Markdown")
    # Ավարտել conversation-ը
    return ConversationHandler.END

# /cancel հրամանի handler, եթե օգտատերը կամենա դադարեցնել
async def cancel(update: Update, context):
    await update.message.reply_text("Հարցումը դադարեցվեց։ Եթե ցանկանում եք սկսեք նորից, ուղարկեք /start։")
    return ConversationHandler.END

if __name__ == "__main__":
    # Ստեղծել Application
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Ստեղծել ConversationHandler states-երով
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, phone_received)],
            ASK_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, branch_received)],
            ASK_EXAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, exam_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # allow_reentry = False (default)
    )

    app.add_handler(conv_handler)

    # Ազատ command-ներ, օրինակ /cancel արդեն ավելացրինք conv_handler-ում
    # Կարող ենք հավելյալ handlers ավելացնել եթե պետք լինի ուրիշ command-ների համար։

    # Ավելացնել մի փոքր help հաղորդագրության համար /help հրամանի աջակցում
    async def help_command(update: Update, context):
        await update.message.reply_text("Օգտագործեք /start որպեսզի սկսել հարցումը վարորդական քննության ազատ ժամերի վերաբերյալ։")
    app.add_handler(CommandHandler("help", help_command))

    # Արտարկել polling mode-ով (երկարաժամկետ)
    app.run_polling(stop_signals=None)  # stop_signals=None նշանակում ենք, որ Ctrl+C-ից բացի այլ signal-ներ չեն կանգնեցնի
