# -*- coding: utf-8 -*-
import logging
import os
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

import config
import database as db
import scraper
import keyboards

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ASK_PHONE, ASK_SOCIAL, SEARCH_EXAM, SEARCH_SERVICE, SEARCH_BRANCH, SEARCH_FILTER, \
ASK_DATE, ASK_HOUR, ASK_WEEKDAY, WAIT_SLOT_SELECT, ASK_EMAIL, WAIT_SMS_CODE = range(12)


def _state(context: CallbackContext) -> Dict[str, Any]:
    if "tmp" not in context.user_data:
        context.user_data["tmp"] = {}
    return context.user_data["tmp"]


def _get_session(user_id: int) -> Tuple[requests.Session, str]:
    u = db.get_user(user_id)
    if u and u.get("cookies"):
        return scraper.ensure_session(u["cookies"])
    return scraper.new_session()


def _save_cookies(user_id: int, sess: requests.Session):
    try:
        db.save_cookies(user_id, scraper.cookies_to_dict(sess.cookies))
    except Exception as e:
        logger.warning("save_cookies failed: %s", e)


# ========== Error handler ==========
def error_handler(update: Optional[Update], context: CallbackContext):
    logger.exception("Unhandled error", exc_info=context.error)
    try:
        if update and update.effective_chat:
            context.bot.send_message(
                update.effective_chat.id,
                "⚠️ Տեխնիկական սխալ առաջացավ։ Խնդրում ենք փորձել կրկին։",
            )
    except Exception:
        pass


# ========== /start ==========
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    context.user_data.clear()
    update.message.reply_text(
        f"Բարի գալուստ, {user.first_name if user and user.first_name else 'օգտագործող'} 👋\n"
        "Խնդրում եմ կիսվեք Ձեր հեռախոսահամարով՝ շարունակելու համար։",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Ուղարկել հեռախոսահամարս", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return ASK_PHONE


def got_phone(update: Update, context: CallbackContext):
    c = update.message.contact
    if not c or not c.phone_number:
        update.message.reply_text("Խնդրում եմ սեղմել «📱 Ուղարկել հեռախոսահամարս» կոճակը։")
        return ASK_PHONE
    st = _state(context)
    st["phone"] = c.phone_number
    update.message.reply_text(
        "Շնորհակալություն։ Խնդրում եմ մուտքագրել Ձեր սոցիալական քարտի համարը (ՀԾՀ, 10 թվանշան)։",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True),
    )
    return ASK_SOCIAL


def got_social(update: Update, context: CallbackContext):
    social = (update.message.text or "").strip()
    if not social.isdigit():
        update.message.reply_text("Խնդրում ենք ուղարկել միայն թվերից բաղկացած ՀԾՀ (օր. 1234567890)։")
        return ASK_SOCIAL

    st = _state(context)
    st["social"] = social
    user_id = update.effective_user.id

    sess, _ = scraper.new_session()
    db.upsert_user(
        user_id=user_id,
        phone=st["phone"],
        social=social,
        cookies=scraper.cookies_to_dict(sess.cookies),
    )
    update.message.reply_text("Գրանցումն ավարտվեց ✅\nՕգտագործեք որոնումը՝ /search")
    return ConversationHandler.END


# ========== helpers for SMS login on-demand ==========
def request_login_and_ask_code(update: Update, context: CallbackContext, sess: requests.Session):
    """Kick off SMS login if services are not visible yet."""
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    if not u or not u.get("phone") or not u.get("social"):
        update.message.reply_text("Խնդրում ենք նախ գրանցվել՝ /start")
        return ConversationHandler.END

    try:
        scraper.login_init(sess, psn=u["social"], phone_number=u["phone"])
        _save_cookies(user_id, sess)
        update.message.reply_text(
            "✅ Հաստատման SMS-ը ուղարկվել է Ձեր հեռախոսին։\n"
            "Խնդրում ենք ուղարկել ստացած 6-նիշ կոդը։"
        )
        return WAIT_SMS_CODE
    except Exception as e:
        logger.warning("login_init failed: %s", e)
        update.message.reply_text("Չհաջողվեց ուղարկել հաստատման կոդը։ Փորձեք կրկին /search։")
        return ConversationHandler.END


def got_sms_code(update: Update, context: CallbackContext):
    code = (update.message.text or "").strip()
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    if not u or not u.get("phone") or not u.get("social"):
        update.message.reply_text("Տվյալները բացակայում են։ Սկսեք /start հրամանով։")
        return ConversationHandler.END

    sess, _ = _get_session(user_id)
    try:
        scraper.login_verify(sess, psn=u["social"], phone_number=u["phone"], token=code)
        _save_cookies(user_id, sess)

        branches, services = scraper.get_branch_and_services(sess)
        if not services:
            update.message.reply_text("Չհաջողվեց բեռնել ծառայությունների ցանկը։ Փորձեք /search։")
            return ConversationHandler.END

        st = _state(context)
        st["branches"] = branches
        st["services_all"] = services
        st["chosen"] = {}

        update.message.reply_text("Մուտքը հաջողվեց ✅\nԸնտրեք քննության տեսակը․",
                                  reply_markup=keyboards.exam_type_keyboard())
        return SEARCH_EXAM
    except Exception as e:
        logger.warning("login_verify failed: %s", e)
        update.message.reply_text("Կոդը սխալ է կամ ժամկետն անցել է։ Կատարեք կրկին /search՝ նորը ստանալու համար։")
        return ConversationHandler.END


# ========== /search ==========
def search_cmd(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        sess, _ = _get_session(user_id)
    except Exception:
        sess, _ = scraper.new_session()

    branches, services = scraper.get_branch_and_services(sess)
    _save_cookies(user_id, sess)

    # If services are not available, require SMS verification
    if not services:
        return request_login_and_ask_code(update, context, sess)

    st = _state(context)
    st["branches"] = branches
    st["services_all"] = services
    st["chosen"] = {}

    update.message.reply_text("Ընտրեք քննության տեսակը․", reply_markup=keyboards.exam_type_keyboard())
    return SEARCH_EXAM


def picked_exam(update: Update, context: CallbackContext):
    exam = (update.message.text or "").strip()
    if exam not in ("Տեսական", "Գործնական"):
        update.message.reply_text("Խնդրում ենք ընտրել «Տեսական» կամ «Գործնական»։")
        return SEARCH_EXAM

    st = _state(context)
    st["chosen"]["exam"] = exam

    services_all: List[Tuple[str, str]] = st.get("services_all", [])
    services = keyboards.filter_services_by_exam(services_all, exam)
    st["services"] = services

    update.message.reply_text(
        "Ընտրեք ծառայությունը․",
        reply_markup=keyboards.list_keyboard_from_pairs(services, cols=2),
    )
    return SEARCH_SERVICE


def picked_service(update: Update, context: CallbackContext):
    label = (update.message.text or "").strip()
    st = _state(context)
    pair = next(((lab, val) for lab, val in st.get("services", []) if lab == label), None)
    if not pair:
        update.message.reply_text("Խնդրում ենք ընտրել ցուցակից։")
        return SEARCH_SERVICE
    st["chosen"]["service_label"], st["chosen"]["service_id"] = pair

    branches: List[Tuple[str, str]] = st.get("branches", [])
    update.message.reply_text(
        "Ընտրեք բաժանմունքը․",
        reply_markup=keyboards.list_keyboard_from_pairs(branches, cols=1),
    )
    return SEARCH_BRANCH


def picked_branch(update: Update, context: CallbackContext):
    label = (update.message.text or "").strip()
    st = _state(context)
    pair = next(((lab, val) for lab, val in st.get("branches", []) if lab == label), None)
    if not pair:
        update.message.reply_text("Խնդրում ենք ընտրել ցուցակից։")
        return SEARCH_BRANCH
    st["chosen"]["branch_label"], st["chosen"]["branch_id"] = pair

    update.message.reply_text("Ընտրեք ֆիլտրի տարբերակը․", reply_markup=keyboards.filter_keyboard())
    return SEARCH_FILTER


def picked_filter(update: Update, context: CallbackContext):
    choice = (update.message.text or "").strip()
    st = _state(context)
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
        update.message.reply_text("Խնդրում ենք ընտրել հասանելի տարբերակներից։")
        return SEARCH_FILTER


def do_nearest(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    st = _state(context)
    branch_id = st["chosen"]["branch_id"]
    service_id = st["chosen"]["service_id"]

    sess, _ = _get_session(user_id)

    # 1) try official endpoint
    day, slots = scraper.nearest_day(sess, branch_id, service_id, "")
    if not day or not slots:
        # 2) fallback: scan forward
        day, slots = scraper.find_nearest_available(sess, branch_id, service_id, max_days=120)

    _save_cookies(user_id, sess)

    if not day:
        update.message.reply_text("Ամենամոտ օր չի գտնվել։ Փորձեք այլ ֆիլտր կամ բաժին/ծառայություն։")
        return ConversationHandler.END

    context.user_data["last_nearest"] = day
    st["chosen"]["date"] = day

    if slots:
        st["chosen"]["slots"] = slots
        update.message.reply_text(
            f"Ամենամոտ օրը՝ {day}\nԸնտրեք ժամերից մեկը՝",
            reply_markup=keyboards.slot_inline_keyboard(slots),
        )
        return WAIT_SLOT_SELECT
    else:
        update.message.reply_text(f"Օր՝ {day}\nՍակայն տվյալ օրվա համար ժամեր չկան։")
        return ConversationHandler.END


def do_all_days(update: Update, context: CallbackContext):
    """Quick view: show 'disabled' days of the month (site exposes just disabled list)."""
    user_id = update.effective_user.id
    st = _state(context)
    branch_id = st["chosen"]["branch_id"]
    service_id = st["chosen"]["service_id"]
    sess, _ = _get_session(user_id)
    today = date.today()
    base = f"{today.day:02d}-{today.month:02d}-{today.year}"
    disabled = scraper.slots_for_month(sess, branch_id, service_id, base)
    _save_cookies(user_id, sess)
    txt = "Անընդունելի օրեր (ամսային ցուցակից)՝ " + (", ".join(disabled) if disabled else "—")
    update.message.reply_text(txt)
    return ConversationHandler.END


def got_date(update: Update, context: CallbackContext):
    dt = (update.message.text or "").strip()
    st = _state(context)
    st["chosen"]["date"] = dt

    user_id = update.effective_user.id
    sess, _ = _get_session(user_id)
    slots = scraper.slots_for_day(sess, st["chosen"]["branch_id"], st["chosen"]["service_id"], dt)
    _save_cookies(user_id, sess)

    if slots:
        st["chosen"]["slots"] = slots
        update.message.reply_text("Հասանելի ժամեր․", reply_markup=keyboards.slot_inline_keyboard(slots))
        return WAIT_SLOT_SELECT

    update.message.reply_text("Տվյալ օրվա համար ժամեր չկան։")
    return ConversationHandler.END


def got_hour(update: Update, context: CallbackContext):
    _state(context)["chosen"]["hour"] = (update.message.text or "").strip()
    return do_nearest(update, context)


def got_weekday(update: Update, context: CallbackContext):
    return do_nearest(update, context)


def slot_clicked(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data or ""
    st = _state(context)

    if data.startswith("slot|"):
        slot_value = data.split("|", 1)[1]
        st["chosen"]["slot_time"] = slot_value
        query.edit_message_text(f"Ընտրված ժամ՝ {slot_value}\nՄուտքագրեք Ձեր email-ը ամրագրման համար։")
        return ASK_EMAIL

    if data.startswith("follow|on"):
        user_id = update.effective_user.id
        db.upsert_tracker(
            user_id,
            st["chosen"]["service_id"],
            st["chosen"]["branch_id"],
            last_best_date=context.user_data.get("last_nearest"),
        )
        query.edit_message_text("🔔 Հետևումը միացված է։")
        return ConversationHandler.END

    if data == "cancel":
        query.edit_message_text("Չեղարկվեց։")
        return ConversationHandler.END

    return ConversationHandler.END


def ask_email_done(update: Update, context: CallbackContext):
    email = (update.message.text or "").strip()
    st = _state(context)
    st["chosen"]["email"] = email
    user_id = update.effective_user.id

    sess, _ = _get_session(user_id)
    try:
        res = scraper.register(
            sess,
            st["chosen"]["branch_id"],
            st["chosen"]["service_id"],
            st["chosen"]["date"],
            st["chosen"]["slot_time"],
            email,
        )
        _save_cookies(user_id, sess)
        pin = res.get("pin") or "—"
        update.message.reply_text(f"✅ Գրանցումն ավարտվեց\nPIN: {pin}")
        update.message.reply_text(
            "Սկսե՞լ հետևել ամենամոտ օրվան այս բաժնի/ծառայության համար:",
            reply_markup=keyboards.confirm_follow_keyboard(),
        )
        return WAIT_SLOT_SELECT
    except Exception as e:
        update.message.reply_text(f"❌ Չհաջողվեց գրանցումը. {e}")
        return ConversationHandler.END


# ======== tracking (global) ========
def tracker_poll(context: CallbackContext):
    try:
        trackers = db.get_all_trackers()
        if not trackers:
            return
        bot = context.bot
        for t in trackers:
            user_id = t.get("tg_user_id") or t.get("user_id")
            branch_id = t.get("branch_id")
            service_id = t.get("service_id")
            last = t.get("last_best_date")
            if not (user_id and branch_id and service_id):
                continue
            sess, _ = _get_session(user_id)
            day, slots = scraper.nearest_day(sess, branch_id, service_id, "")
            if not day or not slots:
                day, slots = scraper.find_nearest_available(sess, branch_id, service_id, max_days=120)
            _save_cookies(user_id, sess)
            if day and (last is None or day < last):
                msg = f"🔔 Գտնվեց ավելի մոտ օր՝ {day}\n/search հրամանով կարող եք ամրագրել։"
                try:
                    bot.send_message(chat_id=user_id, text=msg)
                except Exception:
                    pass
                db.update_tracker_last_date(user_id, service_id, branch_id, day)
    except Exception as e:
        logger.warning("tracker_poll error: %s", e)


# ======== cancel ========
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Գործողությունը դադարեցվեց։")
    return ConversationHandler.END


def main():
    # Updater (ptb v13)
    updater = Updater(token=config.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_error_handler(error_handler)

    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PHONE: [MessageHandler(Filters.contact, got_phone)],
            ASK_SOCIAL: [MessageHandler(Filters.text & ~Filters.command, got_social)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    dp.add_handler(start_conv)

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
            WAIT_SMS_CODE: [MessageHandler(Filters.text & ~Filters.command, got_sms_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    dp.add_handler(search_conv)

    # periodic tracker poll (default 120min)
    updater.job_queue.run_repeating(
        tracker_poll, interval=config.TRACK_INTERVAL_MINUTES * 60, first=60
    )

    # Webhook for Render
    webhook_base = config.WEBHOOK_BASE_URL or os.getenv("RENDER_EXTERNAL_URL", "")
    if not webhook_base:
        raise RuntimeError("WEBHOOK_BASE_URL is required (or set RENDER_EXTERNAL_URL).")
    webhook_path = config.BOT_TOKEN
    updater.start_webhook(
        listen="0.0.0.0",
        port=config.PORT,
        url_path=webhook_path,
        webhook_url=f"{webhook_base.rstrip('/')}/{webhook_path}",
    )
    logging.info("Bot started via webhook on port %s", config.PORT)
    updater.idle()


if __name__ == "__main__":
    main()
