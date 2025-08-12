#!/usr/bin/env python3
import logging
import re
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, CallbackQueryHandler,
    Filters, ConversationHandler, CallbackContext
)

import config
import database as db
import rp_client
import keyboards as kb

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
REG_PHONE, REG_PSN, REG_SMS, MENU_EXAM, MENU_SERVICE, MENU_BRANCH, MENU_FILTER, MENU_WEEKDAY, MENU_DATE, MENU_HOUR, MENU_TIMES, ASK_EMAIL, CONFIRM_BOOK = range(13)

# ephemeral per-chat runtime cache
USER_SESS = {}  # chat_id -> requests.Session
CTX = {}        # chat_id -> dict

def _get_session(chat_id: int):
    sess = USER_SESS.get(chat_id)
    if sess:
        return sess
    # try load cookies from DB
    cookies = db.load_cookies(chat_id)
    sess = rp_client.init_session(seed_cookies=cookies if cookies else None)
    USER_SESS[chat_id] = sess
    return sess

def _validate_phone(s: str) -> bool:
    return bool(re.fullmatch(r"(\+374\d{8}|0\d{8})", s))

def _validate_psn(s: str) -> bool:
    return bool(re.fullmatch(r"\d{10}", s))

def _validate_email(s: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s))

def _today_ddmmYYYY():
    return datetime.now().strftime("%d-%m-%Y")

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    C.clear()

    # Ask phone number (contact button and text hint)
    contact_button = KeyboardButton("📱 Ուղարկել հեռախոսահամարս", request_contact=True)
    update.message.reply_text(
        f"Բարի գալուստ։\n"
        f"Խնդրում եմ ուղարկեք հեռախոսահամարը։\n{config.PHONE_HINT}",
        reply_markup=ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    )
    return REG_PHONE

def reg_phone(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})

    phone = None
    if update.message.contact and update.message.contact.phone_number:
        phone = update.message.contact.phone_number
        # Normalize to +374XXXXXXXX if starts with 374 or 0
        if phone.startswith("374") and len(phone) == 11:
            phone = "+" + phone
        if phone.startswith("0") and len(phone) == 9:
            phone = "+374" + phone[1:]
    else:
        text = (update.message.text or "").strip()
        phone = text

    if not _validate_phone(phone):
        update.message.reply_text(
            f"Հեռախոսահամարը սխալ է։ {config.PHONE_HINT}",
            reply_markup=kb.ok_cancel_kb("Կրկին փորձել", "Չեղարկել"),
        )
        return REG_PHONE

    C["phone"] = phone
    update.message.reply_text(
        "Հաճելի է։ Այժմ մուտքագրեք Ձեր հանրային ծառայության (ՊԳՀ/սոց․քարտ) 10-նիշ համարանիշը։",
    )
    return REG_PSN

def reg_psn(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})

    psn = (update.message.text or "").strip()
    if not _validate_psn(psn):
        update.message.reply_text("Խնդրում ենք մուտքագրել ճիշտ 10-նիշ համար (օր․ 1234567890)։")
        return REG_PSN

    C["psn"] = psn
    # try login
    try:
        resp = rp_client.login(sess, psn=psn, phone=C["phone"], country="374")
    except Exception as e:
        logger.exception("login error")
        update.message.reply_text("Սխալ՝ սերվերի հետ կապը չստացվեց։ Փորձեք նորից /start")
        return ConversationHandler.END

    # Heuristics: if response has something indicating verify step
    text_resp = str(resp).lower()
    if "verify" in text_resp or "sms" in text_resp or "token" in text_resp:
        update.message.reply_text("ՍՄՍ կոդը ուղարկվեց։ Խնդրում ենք մուտքագրել ՍՄՍ կոդը՝ (մինչև 6 թվանշան)։")
        return REG_SMS

    # success without SMS
    db.save_cookies(chat_id, sess.cookies.get_dict())
    db.set_verified(chat_id, True)
    update.message.reply_text(
        "Մուտք գործվեց հաջողությամբ։\n"
        "Օգտագործեք /search՝ ժամանակներ որոնելու համար։"
    )
    return ConversationHandler.END

def reg_code(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    code = (update.message.text or "").strip()
    if not re.fullmatch(r"\d{3,8}", code):
        update.message.reply_text("Մուտքագրեք ճիշտ կոդ (մինչև 8 թվանշան)։")
        return REG_SMS
    try:
        resp = rp_client.verify(sess, code)
    except Exception:
        logger.exception("verify error")
        update.message.reply_text("Սխալ՝ հաստատումը չհաջողվեց։ Փորձեք կրկին /start")
        return ConversationHandler.END

    db.save_cookies(chat_id, sess.cookies.get_dict())
    db.set_verified(chat_id, True)
    update.message.reply_text("Հաստատվեց ✅։ Կարող եք սկսել որոնումը՝ /search")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Գործընթացը դադարեցվեց։")
    return ConversationHandler.END

# ---------------- SEARCH FLOW ----------------

def cmd_search(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    C["flow"] = {}
    update.message.reply_text("Ընտրեք քննության տեսակը․", reply_markup=kb.exam_type_kb())
    return MENU_EXAM

def pick_exam(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})
    choice = (update.message.text or "").strip()

    # Fetch dynamic lists
    try:
        branches, services = rp_client.fetch_branches_and_services(sess)
    except Exception:
        logger.exception("fetch lists error")
        update.message.reply_text("Չհաջողվեց ստանալ ծառայությունների և բաժինների ցանկը։ Փորձեք կրկին /search")
        return ConversationHandler.END

    C["flow"]["branches"] = branches
    C["flow"]["services_all"] = services

    if choice == "Տեսական":
        filtered = [(sid, sname) for sid, sname in services if "տեսակ" in sname.lower()]
    elif choice == "Գործնական":
        filtered = [(sid, sname) for sid, sname in services if "գործն" in sname.lower()]
    else:
        filtered = services

    if not filtered:
        filtered = services

    C["flow"]["services"] = filtered
    update.message.reply_text("Ընտրեք ծառայությունը․", reply_markup=kb.services_kb(filtered))
    return MENU_SERVICE

def pick_service(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    label = (update.message.text or "").strip()
    # map to id
    sid = None
    for s_id, s_name in C["flow"]["services"]:
        if s_name == label:
            sid = s_id; break
    if not sid:
        update.message.reply_text("Խնդրում ենք ընտրել ցանկից։")
        return MENU_SERVICE

    C["flow"]["service_id"] = sid
    update.message.reply_text("Ընտրեք բաժանմունքը․", reply_markup=kb.branches_kb(C["flow"]["branches"]))
    return MENU_BRANCH

def pick_branch(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    label = (update.message.text or "").strip()
    bid = None
    for b_id, b_name in C["flow"]["branches"]:
        if b_name == label:
            bid = b_id; break
    if not bid:
        update.message.reply_text("Խնդրում ենք ընտրել ցանկից։")
        return MENU_BRANCH

    C["flow"]["branch_id"] = bid
    update.message.reply_text("Ընտրեք որոնման տարբերակը․", reply_markup=kb.filter_kb())
    return MENU_FILTER

def pick_filter(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    choice = (update.message.text or "").strip()

    if choice == "Ֆիլտր՝ շաբաթվա օրով":
        update.message.reply_text("Ընտրեք շաբաթվա օրը․", reply_markup=kb.weekdays_kb())
        return MENU_WEEKDAY
    elif choice == "Ֆիլտր՝ ամսաթվով":
        update.message.reply_text(f"Մուտքագրեք ամսաթիվը (ՕՕ-ԱԱ-ՏՏՏՏ)\n{config.DATE_FORMAT_HINT}")
        return MENU_DATE
    elif choice == "Ֆիլտր՝ ժամով":
        update.message.reply_text(f"Մուտքագրեք ժամը (ԺԺ:ՐՐ)\n{config.HOUR_FORMAT_HINT}")
        return MENU_HOUR
    elif choice == "Ամենամոտ օրը":
        return _do_nearest(update, context)
    elif choice == "Բոլոր ազատ օրերը":
        return _do_all_days(update, context)
    else:
        update.message.reply_text("Խնդրում ենք ընտրել առաջարկված տարբերակներից։")
        return MENU_FILTER

def _do_nearest(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})
    b = C["flow"]["branch_id"]; s = C["flow"]["service_id"]

    try:
        resp = rp_client.nearest_day(sess, b, s, _today_ddmmYYYY())
        day = resp.get("data", {}).get("day")
        slots = resp.get("data", {}).get("slots") or []
    except Exception:
        logger.exception("nearest error")
        update.message.reply_text("Չհաջողվեց ստանալ ամենամոտ օրը։")
        return ConversationHandler.END

    if not day or not slots:
        update.message.reply_text("Ազատ մոտ օր暂 չգտնվեց։ Փորձեք «Բոլոր ազատ օրերը» կամ փոխեք բաժինը/ծառայությունը։")
        return ConversationHandler.END

    C["flow"]["date"] = day
    C["flow"]["slots"] = slots
    update.message.reply_text(f"Ամենամոտ ազատ օրը՝ {day}\nԸնտրեք ժամը՝", reply_markup=kb.times_kb(slots))
    return MENU_TIMES

def _iter_dates(n_days: int):
    base = datetime.now()
    for i in range(n_days):
        d = base + timedelta(days=i)
        yield d.strftime("%d-%m-%Y")

def _do_all_days(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})
    b = C["flow"]["branch_id"]; s = C["flow"]["service_id"]

    found = []
    try:
        for d in _iter_dates(config.LOOKAHEAD_DAYS):
            slots = rp_client.slots_for_day(sess, b, s, d)
            if slots:
                found.append((d, len(slots)))
    except Exception:
        logger.exception("list days error")

    if not found:
        update.message.reply_text("Մոտակա օրերի ազատ ժամեր չկան։ Փորձեք փոխել ֆիլտրերը։")
        return ConversationHandler.END

    lines = [f"• {d} — {cnt} ազատ ժամ" for d, cnt in found[:50]]
    update.message.reply_text("Գոյություն ունեցող օրեր՝\n" + "\n".join(lines) + "\n\nՕգտագործեք «Ֆիլտր՝ ամսաթվով»՝ օրը ընտրելու համար։")
    return ConversationHandler.END

def pick_weekday(update: Update, context: CallbackContext):
    wd_map = {
        "Երկուշաբթի": 0, "Երեքշաբթի": 1, "Չորեքշաբթի": 2,
        "Հինգշաբթի": 3, "Ուրբաթ": 4, "Շաբաթ": 5, "Կիրակի": 6
    }
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})
    b = C["flow"]["branch_id"]; s = C["flow"]["service_id"]
    label = (update.message.text or "").strip()
    if label not in wd_map:
        update.message.reply_text("Խնդրում ենք ընտրել շաբաթվա օրվանից։")
        return MENU_WEEKDAY
    want = wd_map[label]

    found = []
    try:
        for d in _iter_dates(config.LOOKAHEAD_DAYS):
            dt = datetime.strptime(d, "%d-%m-%Y")
            if dt.weekday() != want:
                continue
            slots = rp_client.slots_for_day(sess, b, s, d)
            if slots:
                found.append((d, len(slots)))
    except Exception:
        logger.exception("weekday list error")

    if not found:
        update.message.reply_text("Տվյալ շաբաթվա օրով ազատ ժամեր չկան մոտակա ժամանակահատվածում։")
        return ConversationHandler.END

    lines = [f"• {d} — {cnt} ազատ ժամ" for d, cnt in found[:50]]
    update.message.reply_text(f"{label} օրերին առկա օրեր՝\n" + "\n".join(lines) + "\n\nՕգտ․ «Ֆիլտր՝ ամսաթվով»՝ օրը ընտրելու համար։")
    return ConversationHandler.END

def pick_date(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})
    b = C["flow"]["branch_id"]; s = C["flow"]["service_id"]

    d = (update.message.text or "").strip()
    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", d):
        update.message.reply_text(f"Ամսաթիվը սխալ է։ {config.DATE_FORMAT_HINT}")
        return MENU_DATE

    try:
        slots = rp_client.slots_for_day(sess, b, s, d)
    except Exception:
        logger.exception("slots day error")
        update.message.reply_text("Չստացվեց բեռնել ժամերը։")
        return ConversationHandler.END

    if not slots:
        update.message.reply_text(f"{d} օրով ազատ ժամ չկա։ Փորձեք այլ օր։")
        return ConversationHandler.END

    C["flow"]["date"] = d
    C["flow"]["slots"] = slots
    update.message.reply_text(f"{d} օրվա ազատ ժամերը՝ Ընտրեք ժամը։", reply_markup=kb.times_kb(slots))
    return MENU_TIMES

def pick_hour_filter(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})
    b = C["flow"]["branch_id"]; s = C["flow"]["service_id"]

    hhmm = (update.message.text or "").strip()
    if not re.fullmatch(r"\d{2}:\d{2}", hhmm):
        update.message.reply_text(f"Ժամի ֆորմատը սխալ է։ {config.HOUR_FORMAT_HINT}")
        return MENU_HOUR

    found = []
    try:
        for d in _iter_dates(config.LOOKAHEAD_DAYS):
            slots = rp_client.slots_for_day(sess, b, s, d)
            if any((sl.get("value") == hhmm or sl.get("label") == hhmm) for sl in slots):
                found.append(d)
    except Exception:
        logger.exception("hour filter error")

    if not found:
        update.message.reply_text(f"Մոտակա {config.LOOKAHEAD_DAYS} օրում {hhmm}-ին ազատ ժամեր չկան։")
        return ConversationHandler.END

    update.message.reply_text("Համապատասխան օրեր՝\n" + "\n".join(f"• {d}" for d in found[:50]))
    return ConversationHandler.END

def pick_time(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    label = (update.message.text or "").strip()
    slots = C["flow"].get("slots") or []
    slot = next((sl for sl in slots if (sl.get("label") == label or sl.get("value") == label)), None)
    if not slot:
        update.message.reply_text("Խնդրում ենք ընտրել ժամերը ցուցակից։")
        return MENU_TIMES

    C["flow"]["slot_time"] = slot.get("value") or slot.get("label")
    update.message.reply_text(f"Մուտքագրեք Ձեր էլ․ փոստը ամրագրման համար։\n{config.EMAIL_HINT}")
    return ASK_EMAIL

def ask_email(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    C = CTX.setdefault(chat_id, {})
    email = (update.message.text or "").strip()
    if not _validate_email(email):
        update.message.reply_text("Էլ․ փոստի ֆորմատը սխալ է։ Կրկին մուտքագրեք։")
        return ASK_EMAIL
    C["flow"]["email"] = email

    b = C["flow"]["branch_id"]
    s = C["flow"]["service_id"]
    d = C["flow"]["date"]
    t = C["flow"]["slot_time"]
    update.message.reply_text(
        f"Հաստատո՞ւմ եք ամրագրումը.\n"
        f"• Բաժին՝ {b}\n• Ծառայություն՝ {s}\n• Ամսաթիվ՝ {d}\n• Ժամ՝ {t}\n• Email՝ {email}",
        reply_markup=kb.yes_no_kb()
    )
    return CONFIRM_BOOK

def confirm_book(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sess = _get_session(chat_id)
    C = CTX.setdefault(chat_id, {})

    if (update.message.text or "").strip() != "Այո":
        update.message.reply_text("Չեղարկվեց։")
        return ConversationHandler.END

    try:
        resp = rp_client.register_slot(sess,
            C["flow"]["branch_id"], C["flow"]["service_id"], C["flow"]["date"],
            C["flow"]["slot_time"], C["flow"]["email"]
        )
        pin = resp.get("pin") or ""
        msg = "Ամրագրումը հաջողվեց ✅"
        if pin:
            msg += f"\nՁեր PIN՝ {pin}"
        update.message.reply_text(msg)
    except Exception:
        logger.exception("register error")
        update.message.reply_text("Ամրագրումը չստացվեց։ Փորձեք կրկին։")
        return ConversationHandler.END

    # save latest cookies
    db.save_cookies(chat_id, sess.cookies.get_dict())
    return ConversationHandler.END

# ------------- TELEGRAM WIRING -------------

def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    updater = Updater(token=config.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Registration conversation
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_PHONE: [
                MessageHandler(Filters.contact, reg_phone),
                MessageHandler(Filters.text & ~Filters.command, reg_phone),
            ],
            REG_PSN: [MessageHandler(Filters.text & ~Filters.command, reg_psn)],
            REG_SMS: [MessageHandler(Filters.text & ~Filters.command, reg_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="reg_conv",
        persistent=False,
        per_user=True,
        per_chat=True,
    )

    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", cmd_search)],
        states={
            MENU_EXAM: [MessageHandler(Filters.text & ~Filters.command, pick_exam)],
            MENU_SERVICE: [MessageHandler(Filters.text & ~Filters.command, pick_service)],
            MENU_BRANCH: [MessageHandler(Filters.text & ~Filters.command, pick_branch)],
            MENU_FILTER: [MessageHandler(Filters.text & ~Filters.command, pick_filter)],
            MENU_WEEKDAY: [MessageHandler(Filters.text & ~Filters.command, pick_weekday)],
            MENU_DATE: [MessageHandler(Filters.text & ~Filters.command, pick_date)],
            MENU_HOUR: [MessageHandler(Filters.text & ~Filters.command, pick_hour_filter)],
            MENU_TIMES: [MessageHandler(Filters.text & ~Filters.command, pick_time)],
            ASK_EMAIL: [MessageHandler(Filters.text & ~Filters.command, ask_email)],
            CONFIRM_BOOK: [MessageHandler(Filters.text & ~Filters.command, confirm_book)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="search_conv",
        persistent=False,
        per_user=True,
        per_chat=True,
    )

    dp.add_handler(reg_conv)
    dp.add_handler(search_conv)

    # Webhook mode for Render
    if config.WEBHOOK_BASE_URL:
        webhook_path = f"/bot/{config.BOT_TOKEN}"
        updater.start_webhook(listen="0.0.0.0", port=config.PORT, url_path=webhook_path)
        updater.bot.set_webhook(url=f"{config.WEBHOOK_BASE_URL}{webhook_path}")
        logger.info("Bot started via webhook on port %s", config.PORT)
        updater.idle()
    else:
        # Polling fallback (local/dev)
        logger.info("Starting bot with long polling…")
        updater.start_polling(clean=True)
        updater.idle()

if __name__ == "__main__":
    main()
