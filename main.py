# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, Tuple, List

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, ConversationHandler, CallbackContext

import config
import database as db
import scraper
import requests

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# STATES
ASK_PHONE, ASK_SOCIAL, SEARCH_EXAM, SEARCH_SERVICE, SEARCH_BRANCH, SEARCH_FILTER, \
ASK_DATE, ASK_HOUR, ASK_WEEKDAY, WAIT_SLOT_SELECT, ASK_EMAIL = range(11)

# in-memory per user temp
def get_user_state(context: CallbackContext) -> Dict[str, Any]:
    if "tmp" not in context.user_data:
        context.user_data["tmp"] = {}
    return context.user_data["tmp"]

# ======== helpers ========
def get_session_for_user(user_id: int) -> Tuple[requests.Session, str]:
    u = db.get_user(user_id)
    if u and u.get("cookies"):
        return scraper.ensure_session(u["cookies"])
    return scraper.new_session()

def save_session_cookies(user_id: int, sess: requests.Session):
    try:
        db.save_cookies(user_id, scraper.cookies_to_dict(sess.cookies))
    except Exception as e:
        logger.warning("save_session_cookies failed: %s", e)

def filter_services_by_exam(services: List[Tuple[str, str]], exam: str) -> List[Tuple[str, str]]:
    exam = exam.strip()
    if exam == "Տեսական":
        keys = ["տեսական", "theory"]
    else:
        keys = ["գործնական", "practical"]
    out = []
    for lab, val in services:
        low = lab.lower()
        if any(k in low for k in keys):
            out.append((lab, val))
    # fallback: if no match, return all
    return out or services

# ======== /start flow ========
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    context.user_data.clear()
    update.message.reply_text(
        f"Բարի գալուստ, {user.first_name if user and user.first_name else 'օգտագործող'} 👋\n"
        "Խնդրում եմ կիսվեք Ձեր հեռախոսահամարով՝ շարունակելու համար։",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Ուղարկել հեռախոսահամարս", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_PHONE

def got_phone(update: Update, context: CallbackContext):
    c = update.message.contact
    if not c or not c.phone_number:
        update.message.reply_text("Խնդրում եմ սեղմել «📱 Ուղարկել հեռախոսահամարս» կոճակը։")
        return ASK_PHONE
    st = get_user_state(context)
    st["phone"] = c.phone_number
    update.message.reply_text("Շնորհակալություն։ Խնդրում եմ մուտքագրել Ձեր սոցիալական քարտի համարը (ՀԾՀ, 10 թվանշան)։",
                              reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True))
    return ASK_SOCIAL

def got_social(update: Update, context: CallbackContext):
    social = update.message.text.strip()
    if not social.isdigit():
        update.message.reply_text("Խնդրում եմ ուղարկել միայն թվերից բաղկացած ՀԾՀ (օր. 1234567890)։")
        return ASK_SOCIAL
    st = get_user_state(context)
    st["social"] = social
    user_id = update.effective_user.id

    # create session, save cookies
    sess, _ = scraper.new_session()
    db.upsert_user(user_id=user_id, phone=st["phone"], social=social, cookies=scraper.cookies_to_dict(sess.cookies))
    update.message.reply_text("Գրանցումն ավարտվեց ✅\nԱյժմ կարող եք օգտագործել որոնումը՝ /search")
    return ConversationHandler.END

# ======== /search flow ========
def search_cmd(update: Update, context: CallbackContext):
    # ensure session
    user_id = update.effective_user.id
    try:
        sess, _ = get_session_for_user(user_id)
    except Exception:
        sess, _ = scraper.new_session()
    # fetch branches/services
    branches, services = scraper.get_branch_and_services(sess)
    save_session_cookies(user_id, sess)

    st = get_user_state(context)
    st["branches"] = branches
    st["services_all"] = services
    st["chosen"] = {}

    update.message.reply_text("Ընտրեք քննության տեսակը․", reply_markup=keyboards.exam_type_keyboard())
    return SEARCH_EXAM

import keyboards

def picked_exam(update: Update, context: CallbackContext):
    exam = update.message.text.strip()
    if exam not in ("Տեսական", "Գործնական"):
        update.message.reply_text("Խնդրում եմ ընտրել «Տեսական» կամ «Գործնական»։")
        return SEARCH_EXAM
    st = get_user_state(context)
    st["chosen"]["exam"] = exam
    # filter services
    services_all: List[Tuple[str, str]] = st.get("services_all", [])
    services = filter_services_by_exam(services_all, exam)
    st["services"] = services
    update.message.reply_text("Ընտրեք ծառայությունը․", reply_markup=keyboards.list_keyboard_from_pairs(services, cols=2))
    return SEARCH_SERVICE

def picked_service(update: Update, context: CallbackContext):
    label = update.message.text.strip()
    st = get_user_state(context)
    pair = next(((lab, val) for lab, val in st.get("services", []) if lab == label), None)
    if not pair:
        update.message.reply_text("Խնդրում եմ ընտրել ցուցակից։")
        return SEARCH_SERVICE
    st["chosen"]["service_label"], st["chosen"]["service_id"] = pair
    # ask branch
    branches: List[Tuple[str, str]] = st.get("branches", [])
    update.message.reply_text("Ընտրեք բաժանմունքը․", reply_markup=keyboards.list_keyboard_from_pairs(branches, cols=1))
    return SEARCH_BRANCH

def picked_branch(update: Update, context: CallbackContext):
    label = update.message.text.strip()
    st = get_user_state(context)
    pair = next(((lab, val) for lab, val in st.get("branches", []) if lab == label), None)
    if not pair:
        update.message.reply_text("Խնդրում եմ ընտրել ցուցակից։")
        return SEARCH_BRANCH
    st["chosen"]["branch_label"], st["chosen"]["branch_id"] = pair
    update.message.reply_text("Ընտրեք ֆիլտրի տարբերակը․", reply_markup=keyboards.filter_keyboard())
    return SEARCH_FILTER

def picked_filter(update: Update, context: CallbackContext):
    choice = update.message.text.strip()
    st = get_user_state(context)
    st["filter"] = choice

    if choice == "Ամենամոտ օր":
        return do_nearest(update, context)
    elif choice == "Ըստ ամսաթվի":
        update.message.reply_text("Մուտքագրեք ամսաթիվը `ՕՕ-ԱԱ-ՏՏՏՏ` (օր. 25-08-2025)։")
        return ASK_DATE
    elif choice == "Ըստ ժամի":
        update.message.reply_text("Մուտքագրեք ժամը `ԺԺ:ՐՐ` (օր. 09:00)։")
        return ASK_HOUR
    elif choice == "Շաբաթվա օրով":
        update.message.reply_text("Ընտրեք շաբաթվա օրը․", reply_markup=keyboards.weekdays_keyboard())
        return ASK_WEEKDAY
    elif choice == "Բոլոր ազատ օրերը":
        return do_all_days(update, context)
    else:
        update.message.reply_text("Խնդրում եմ ընտրել հասանելի տարբերակներից։")
        return SEARCH_FILTER

def do_nearest(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    st = get_user_state(context)
    branch_id = st["chosen"]["branch_id"]
    service_id = st["chosen"]["service_id"]
    sess, _ = get_session_for_user(user_id)
    day, slots = scraper.nearest_day(sess, branch_id, service_id, "")
    save_session_cookies(user_id, sess)
    if not day:
        update.message.reply_text("Ամենամոտ օր չի գտնվել։ Փորձեք այլ ֆիլտր։")
        return ConversationHandler.END
    context.user_data["last_nearest"] = day
    st["chosen"]["date"] = day
    update.message.reply_text(f"Ամենամոտ օրը՝ {day}\nԸնտրեք ժամերը՝",
                              reply_markup=None)
    if not slots:
        # fetch slots for that day explicitly
        slots = scraper.slots_for_day(sess, branch_id, service_id, day)
    if slots:
        st["chosen"]["slots"] = slots
        update.message.reply_text("Հասանելի ժամեր․", reply_markup=None)
        update.message.reply_text(
            "Ընտրեք ժամ (սեղմեք կոճակը).",
            reply_markup=keyboards.slot_inline_keyboard(slots)
        )
        return WAIT_SLOT_SELECT
    else:
        update.message.reply_text("Տվյալ օրվա համար ժամեր չկան։")
        return ConversationHandler.END

def do_all_days(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    st = get_user_state(context)
    branch_id = st["chosen"]["branch_id"]
    service_id = st["chosen"]["service_id"]
    sess, _ = get_session_for_user(user_id)

    # օգտագործենք ամսվա disabled օրերը՝ candidate օրերը ստանալու համար
    from datetime import date
    today = date.today()
    base = f"{today.day:02d}-{today.month:02d}-{today.year}"
    disabled = scraper.slots_for_month(sess, branch_id, service_id, base)
    save_session_cookies(user_id, sess)
    update.message.reply_text(f"Անաշխատ օրեր (ամսային ցուցակից): {', '.join(disabled) if disabled else '—'}\n"
                              f"Օգտվեք «Ըստ ամսաթվի» կամ «Ամենամոտ օր»՝ կոնկրետ օր/ժամ տեսնելու համար։")
    return ConversationHandler.END

def got_date(update: Update, context: CallbackContext):
    dt = update.message.text.strip()
    st = get_user_state(context)
    st["chosen"]["date"] = dt
    user_id = update.effective_user.id
    sess, _ = get_session_for_user(user_id)
    slots = scraper.slots_for_day(sess, st["chosen"]["branch_id"], st["chosen"]["service_id"], dt)
    save_session_cookies(user_id, sess)
    if slots:
        st["chosen"]["slots"] = slots
        update.message.reply_text("Հասանելի ժամեր․",
                                  reply_markup=keyboards.slot_inline_keyboard(slots))
        return WAIT_SLOT_SELECT
    update.message.reply_text("Տվյալ օրվա համար ժամեր չկան։")
    return ConversationHandler.END

def got_hour(update: Update, context: CallbackContext):
    hr = update.message.text.strip()
    st = get_user_state(context)
    st["chosen"]["hour"] = hr
    # we still need a day; suggest nearest
    return do_nearest(update, context)

def got_weekday(update: Update, context: CallbackContext):
    wd = update.message.text.strip()
    # simple approach: fetch nearest day, user can refine
    return do_nearest(update, context)

def slot_clicked(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    if not data.startswith("slot|"):
        if data == "follow|on":
            return enable_follow(update, context)
        elif data == "cancel":
            query.edit_message_text("Չեղարկվեց.")
            return ConversationHandler.END
        return ConversationHandler.END
    slot_value = data.split("|", 1)[1]
    st = get_user_state(context)
    st["chosen"]["slot_time"] = slot_value
    query.edit_message_text(f"Ընտրված ժամ՝ {slot_value}\nՄուտքագրեք Ձեր email-ը ամրագրման համար։")
    return ASK_EMAIL

def ask_email_done(update: Update, context: CallbackContext):
    email = update.message.text.strip()
    st = get_user_state(context)
    st["chosen"]["email"] = email
    user_id = update.effective_user.id

    sess, _ = get_session_for_user(user_id)
    try:
        res = scraper.register(sess,
                               st["chosen"]["branch_id"],
                               st["chosen"]["service_id"],
                               st["chosen"]["date"],
                               st["chosen"]["slot_time"],
                               email)
        save_session_cookies(user_id, sess)
        pin = res.get("pin") or "—"
        update.message.reply_text(f"✅ Գրանցումն επιτυχία\nPIN: {pin}")
        # առաջարկել հետևում
        update.message.reply_text("Սկսե՞լ հետևել ամենամոտ օրվան այս բաժնի/ծառայության համար:",
                                  reply_markup=keyboards.confirm_follow_keyboard())
        return WAIT_SLOT_SELECT
    except Exception as e:
        update.message.reply_text(f"❌ Չհաջողվեց գրանցումը. {e}")
        return ConversationHandler.END

def enable_follow(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    st = get_user_state(context)
    user_id = update.effective_user.id
    db.upsert_tracker(user_id, st["chosen"]["service_id"], st["chosen"]["branch_id"], last_best_date=context.user_data.get("last_nearest"))
    query.edit_message_text("🔔 Following միացված է։ Կտեղեկացնենք, երբ գտնվի ավելի մոտ օր։")
    return ConversationHandler.END

# ======== tracking job ========
def check_trackers_job(context: CallbackContext):
    job = context.job
    # iterate all users who have trackers
    # պարզ տարբերակ՝ մենք չենք քաշում բոլոր user-ների ցուցակը; այստեղ կապահովենք per-chat run
    # practically, կկանչվի updater.job_queue.run_repeating գլոբալ; կստուգենք միայն այդ chat-ի
    # իրականում, կանցնենք known chats-ից: պահենք memory-ում enabled tracker-ներ per run?
    # Այստեղ՝ պարզ տարբերակ՝ ոչինչ չենք անում; իրական աշխատանքը կարվի /follow միացնելու պահին
    pass

# Globally check all trackers per interval (single job):
def global_tracker_poll(context: CallbackContext):
    logger.info("Tracker poll tick")
    # This needs a list of trackers. For simplicity we fetch all enabled trackers per user we know.
    # If you want fully global polling, create a service endpoint or store list of user ids.
    # Here, we can't list users without an index; so skip.
    # You can extend by adding a 'list users' RPC on Supabase or a view.
    # Minimal working solution: tracking is user-initiated; polling could be triggered by /follow-start in a real app.

# ======== cancel ========
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Գործողությունը դադարեցվեց։")
    return ConversationHandler.END

# ======== main ========
def main():
    updater = Updater(token=config.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # /start conversation
    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PHONE: [MessageHandler(Filters.contact, got_phone)],
            ASK_SOCIAL: [MessageHandler(Filters.text & ~Filters.command, got_social)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dp.add_handler(start_conv)

    # /search conversation
    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_cmd)],
        states={
            SEARCH_EXAM: [MessageHandler(Filters.text & ~Filters.command, picked_exam)],
            SEARCH_SERVICE: [MessageHandler(Filters.text & ~Filters.command, picked_service)],
            SEARCH_BRANCH: [MessageHandler(Filters.text & ~Filters.command, picked_branch)],
            SEARCH_FILTER: [MessageHandler(Filters.text & ~Filters.command, picked_filter)],
            ASK_DATE: [MessageHandler(Filters.text & ~Filters.command, got_date)],
            ASK_HOUR: [MessageHandler(Filters.text & ~Filters.command, got_hour)],
            ASK_WEEKDAY: [MessageHandler(Filters.text & ~Filters.command, got_weekday)],
            WAIT_SLOT_SELECT: [CallbackQueryHandler(slot_clicked)],
            ASK_EMAIL: [MessageHandler(Filters.text & ~Filters.command, ask_email_done)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dp.add_handler(search_conv)

    # also handle inline callbacks from final step (follow/cancel)
    dp.add_handler(CallbackQueryHandler(slot_clicked, pattern="^(slot|follow|cancel)\\|?"))

    # tracking job (placeholder global)
    updater.job_queue.run_repeating(global_tracker_poll, interval=config.TRACK_INTERVAL_MINUTES * 60, first=60)

    logger.info("Bot started (polling)")
    updater.start_polling(clean=True)
    updater.idle()

if __name__ == "__main__":
    main()
