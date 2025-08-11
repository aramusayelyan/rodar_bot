# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, ConversationHandler, CallbackContext

import config
import database as db
import scraper
import keyboards as kb

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# States
REG_PHONE, REG_SOCIAL, REG_CODE = range(3)
SVC, BRANCH, FILT, WEEKDAY, DATE, HOUR, CONFIRM, EMAIL = range(8)

# In-memory session storage key
SESSIONS = {}  # user_id -> {"sess": requests.Session, "csrf": str}

def _get_or_build_session(user_id: int, cookies: dict = None):
    if user_id in SESSIONS:
        return SESSIONS[user_id]["sess"], SESSIONS[user_id]["csrf"]
    sess, csrf = scraper.ensure_session(cookies=cookies)
    SESSIONS[user_id] = {"sess": sess, "csrf": csrf}
    return sess, csrf

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    if u:
        update.message.reply_text(
            "Դուք արդեն գրանցված եք։ Օգտվեք /search հրամանով՝ ազատ օրեր գտնելու համար։"
        )
        return ConversationHandler.END
    contact_btn = KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)
    update.message.reply_text(
        "Բարի գալուստ։ Սկսենք գրանցումից։ Խնդրում ենք ուղարկել Ձեր հեռախոսահամարը։",
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True),
    )
    return REG_PHONE

def reg_phone(update: Update, context: CallbackContext):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    context.user_data["phone"] = phone
    update.message.reply_text("Խնդրում ենք մուտքագրել Ձեր սոցիալական քարտի համարը (ՀԾՀ):",
                              reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True))
    return REG_SOCIAL

def reg_social(update: Update, context: CallbackContext):
    social = update.message.text.strip()
    phone = context.user_data.get("phone")
    # start login flow (send code if needed)
    ok, sess, csrf = scraper.login_send_code(social, phone)
    if not ok:
        update.message.reply_text("Չհաջողվեց սկսել նույնականացումը։ Փորձեք կրկին /start։")
        return ConversationHandler.END
    # keep session
    SESSIONS[update.effective_user.id] = {"sess": sess, "csrf": csrf}
    update.message.reply_text("Եթե սմս կոդ է ստացվել, մուտքագրեք այն։ Եթե չի պահանջվում՝ ուղարկեք «0».")
    return REG_CODE

def reg_code(update: Update, context: CallbackContext):
    code = update.message.text.strip()
    phone = context.user_data.get("phone")
    social = context.user_data.get("social") or update.message.text.strip()
    user_id = update.effective_user.id
    sess, _ = _get_or_build_session(user_id)
    success = True
    if code != "0":
        success = scraper.login_verify_code(sess, social, phone, code)
    if not success:
        update.message.reply_text("ՍՄՍ կոդի հաստատումը ձախողվեց։ Փորձեք կրկին /start։")
        return ConversationHandler.END
    # save user and cookies
    cookies = sess.cookies.get_dict()
    db.upsert_user(user_id=user_id, phone=phone, social=social, cookies=cookies)
    update.message.reply_text("Գրանցումը ավարտվեց հաջողությամբ։ Կարող եք սկսել որոնումը՝ /search")
    return ConversationHandler.END

def search_entry(update: Update, context: CallbackContext):
    # choose service
    update.message.reply_text("Ընտրեք քննության տեսակը․", reply_markup=kb.build_inline(kb.SERVICES, cols=1))
    return SVC

def pick_service(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    service_id = q.data
    context.user_data["service_id"] = service_id
    # branches dynamic
    branches = scraper.get_branches()
    context.user_data["branches"] = branches
    q.edit_message_text("Ընտրեք բաժանմունքը․", reply_markup=kb.build_inline(branches, cols=1))
    return BRANCH

def pick_branch(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    branch_id = q.data
    context.user_data["branch_id"] = branch_id
    q.edit_message_text("Ընտրեք որոնման տարբերակը․", reply_markup=kb.build_inline(kb.FILTERS, cols=1))
    return FILT

def pick_filter(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    choice = q.data
    context.user_data["filter"] = choice
    if choice == "closest":
        # compute closest and offer tracking
        user_id = update.effective_user.id
        u = db.get_user(user_id)
        sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies") if u else None)
        svc = context.user_data["service_id"]
        br = context.user_data["branch_id"]
        res = scraper.find_closest_slot(sess, br, svc)
        if not res:
            q.edit_message_text("Մոտակա ազատ օր չի գտնվել։ Ակտիվացնե՞լ մշտական հետևումը՝ հայտնելու դեպքում ձեզ տեղեկացնելու জন্য։",
                                reply_markup=kb.build_inline([("Այո", "track_yes"), ("Ոչ", "track_no")], cols=2))
            return CONFIRM
        date_iso, time_str = res
        context.user_data["sel_date"] = date_iso
        context.user_data["sel_time"] = time_str
        msg = f"Ամենամոտ օր․ {date_iso} ժամը {time_str}։ Գրանցվե՞լ այս ժամանակի համար, կամ ակտիվացնե՞լ մշտական հետևում։"
        q.edit_message_text(msg, reply_markup=kb.build_inline([("Գրանցել հիմա", "book_now"),
                                                              ("Ակտիվացնել հետևումը", "track_yes"),
                                                              ("Չեղարկել", "track_no")], cols=1))
        return CONFIRM
    elif choice == "weekday":
        q.edit_message_text("Ընտրեք շաբաթվա օրը․", reply_markup=kb.build_inline(kb.WEEKDAYS, cols=2))
        return WEEKDAY
    elif choice == "date":
        q.edit_message_text("Մուտքագրեք ամսաթիվը `ՕՕ/ԱԱ/ՏՏՏՏ` ֆորմատով (օր․ 25/08/2025)։")
        return DATE
    elif choice == "hour":
        q.edit_message_text("Մուտքագրեք ժամը (0-23)՝ օրինակ `14`։")
        return HOUR
    elif choice == "all":
        user_id = update.effective_user.id
        u = db.get_user(user_id)
        sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies") if u else None)
        svc = context.user_data["service_id"]; br = context.user_data["branch_id"]
        now = datetime.now()
        lines = []
        for mo in range(3):
            y = now.year + ((now.month - 1 + mo) // 12)
            m = ((now.month - 1 + mo) % 12) + 1
            days = scraper.fetch_available_days(sess, br, svc, y, m)
            for d in days:
                di = d
                if re.match(r"^\d{2}\.\d{2}\.\d{4}$", d):
                    di = datetime.strptime(d, "%d.%m.%Y").strftime("%Y-%m-%d")
                times = scraper.fetch_available_times(sess, br, svc, di)
                if times:
                    lines.append(f"{di}: {', '.join(times)}")
        if not lines:
            q.edit_message_text("Առաջիկա ամիսների համար ազատ ժամեր չեն գտնվել։")
        else:
            txt = "Ազատ ժամեր՝\n" + "\n".join(lines[:60])
            q.edit_message_text(txt)
        return ConversationHandler.END

def choose_weekday(update: Update, context: CallbackContext):
    import re
    q = update.callback_query
    q.answer()
    wd = int(q.data)
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies") if u else None)
    svc = context.user_data["service_id"]; br = context.user_data["branch_id"]
    now = datetime.now()
    for d in range(0, 90):
        dt = now + timedelta(days=d)
        if dt.weekday() == wd:
            di = dt.strftime("%Y-%m-%d")
            ts = scraper.fetch_available_times(sess, br, svc, di)
            if ts:
                context.user_data["sel_date"] = di
                context.user_data["sel_time"] = ts[0]
                q.edit_message_text(f"Առաջիկա {di}՝ ժամը {ts[0]}։ Գրանցվե՞լ։",
                                    reply_markup=kb.build_inline([("Այո, գրանցել", "book_now"), ("Ոչ", "track_no")], cols=2))
                return CONFIRM
    q.edit_message_text("Տրված շաբաթվա օրվա համար ժամանակ չի գտնվել մոտ 90 օրվա ընթացքում։")
    return ConversationHandler.END

def input_date(update: Update, context: CallbackContext):
    import re
    t = update.message.text.strip()
    try:
        d, m, y = map(int, re.split(r"[./-]", t))
        date_iso = datetime(y, m, d).strftime("%Y-%m-%d")
    except Exception:
        update.message.reply_text("Սխալ ձևաչափ։ Օրինակ՝ 05/09/2025")
        return DATE
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies") if u else None)
    svc = context.user_data["service_id"]; br = context.user_data["branch_id"]
    ts = scraper.fetch_available_times(sess, br, svc, date_iso)
    if not ts:
        update.message.reply_text(f"{date_iso} օրվա համար ազատ ժամեր չկան։")
        return ConversationHandler.END
    context.user_data["sel_date"] = date_iso
    context.user_data["sel_time"] = ts[0]
    update.message.reply_text(f"{date_iso}՝ {ts[0]}։ Գրանցվե՞լ։",
                              reply_markup=kb.build_inline([("Այո, գրանցել", "book_now"), ("Ոչ", "track_no")], cols=2))
    return CONFIRM

def input_hour(update: Update, context: CallbackContext):
    t = update.message.text.strip()
    if not t.isdigit():
        update.message.reply_text("Մուտքագրեք ամբողջ ժամ՝ օրինակ 14")
        return HOUR
    want = int(t); 
    if want < 0 or want > 23:
        update.message.reply_text("Ժամը պետք է լինի 0-23 միջակայքում")
        return HOUR
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies") if u else None)
    svc = context.user_data["service_id"]; br = context.user_data["branch_id"]
    now = datetime.now()
    for d in range(0, 90):
        di = (now + timedelta(days=d)).strftime("%Y-%m-%d")
        ts = scraper.fetch_available_times(sess, br, svc, di)
        for hhmm in ts:
            try:
                hh = int(hhmm.split(":")[0])
                if hh == want:
                    context.user_data["sel_date"] = di
                    context.user_data["sel_time"] = hhmm
                    update.message.reply_text(f"Առաջին հասանելի {want}:00-ը՝ {di}՝ {hhmm}։ Գրանցվե՞լ։",
                                              reply_markup=kb.build_inline([("Այո, գրանցել", "book_now"), ("Ոչ", "track_no")], cols=2))
                    return CONFIRM
            except Exception:
                continue
    update.message.reply_text("Մոտ కాలում այդ ժամին ազատ կտրոն չի գտնվել։")
    return ConversationHandler.END

def confirm_stage(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    action = q.data
    if action == "track_no":
        q.edit_message_text("Չեղարկվեց։")
        return ConversationHandler.END
    if action == "track_yes":
        # enable tracker
        user_id = update.effective_user.id
        svc = context.user_data["service_id"]; br = context.user_data["branch_id"]
        db.upsert_tracker(user_id, svc, br, last_best_date=None, enabled=True)
        # schedule job
        context.job_queue.run_repeating(check_tracker_job, interval=config.TRACK_INTERVAL_MINUTES * 60,
                                        first=10, context={"user_id": user_id, "service_id": svc, "branch_id": br},
                                        name=f"track:{user_id}:{svc}:{br}")
        q.edit_message_text("Մշտական հետևումը ակտիվացված է։ Երբ ավելի մոտիկ օր գտնվի՝ կտեղեկացնենք։")
        return ConversationHandler.END
    if action == "book_now":
        # ensure email
        user_id = update.effective_user.id
        u = db.get_user(user_id)
        if not u.get("email"):
            q.edit_message_text("Մուտքագրեք Ձեր էլ․ փոստը՝ ամրագրումը ավարտելու համար։")
            return EMAIL
        # otherwise book
        return do_booking(q, context, u["email"])

def receive_email(update: Update, context: CallbackContext):
    email = update.message.text.strip()
    user_id = update.effective_user.id
    db.update_user(user_id, {"email": email})
    return do_booking(update, context, email)

def do_booking(carrier, context: CallbackContext, email: str):
    # carrier can be CallbackQuery or Message
    user_id = carrier.effective_user.id if hasattr(carrier, "effective_user") else context._user_id_and_data[0]
    u = db.get_user(user_id)
    sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies") if u else None)
    svc = context.user_data["service_id"]; br = context.user_data["branch_id"]
    di = context.user_data["sel_date"]; hhmm = context.user_data["sel_time"]
    ok = scraper.book_appointment(sess, br, svc, di, hhmm, email)
    if ok:
        text = "Ամրագրումը հաջողվեց ✅"
    else:
        text = "Ամրագրումը չհաջողվեց ❌ (կտրոնը կարող է զբաղված լինել)"
    if hasattr(carrier, "edit_message_text"):
        carrier.edit_message_text(text)
    else:
        carrier.message.reply_text(text)
    return ConversationHandler.END

def check_tracker_job(context: CallbackContext):
    job = context.job
    data = job.context or {}
    user_id = data.get("user_id"); svc = data.get("service_id"); br = data.get("branch_id")
    if not user_id or not svc or not br:
        return
    u = db.get_user(user_id)
    if not u or not u.get("cookies"):
        return
    sess, _ = _get_or_build_session(user_id, cookies=u.get("cookies"))
    # find closest now
    res = scraper.find_closest_slot(sess, br, svc)
    if not res:
        return
    date_iso, time_str = res
    # compare with last_best_date from DB
    trackers = db.get_trackers_for_user(user_id)
    last = None
    for t in trackers:
        if t["service_id"] == svc and t["branch_id"] == br:
            last = t.get("last_best_date")
            break
    def date_tuple(x: str):
        return tuple(map(int, x.split("-")))
    should_notify = False
    if last:
        try:
            should_notify = date_tuple(date_iso) < date_tuple(last)
        except Exception:
            should_notify = (date_iso != last)
    else:
        should_notify = True
    if should_notify:
        context.bot.send_message(chat_id=user_id,
                                 text=f"Նոր՝ ավելի մոտ օր գտանք․ {date_iso} ժամը {time_str}")
        db.update_tracker_last_date(user_id, svc, br, date_iso)

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Գործողությունը դադարեցվեց։")
    return ConversationHandler.END

def main():
    updater = Updater(token=config.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_PHONE: [MessageHandler(Filters.contact | Filters.text, reg_phone)],
            REG_SOCIAL: [MessageHandler(Filters.text & ~Filters.command, reg_social)],
            REG_CODE: [MessageHandler(Filters.text & ~Filters.command, reg_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_entry)],
        states={
            SVC: [CallbackQueryHandler(pick_service, pattern=r"^\d+$")],
            BRANCH: [CallbackQueryHandler(pick_branch, pattern=r"^\d+$")],
            FILT: [CallbackQueryHandler(pick_filter, pattern=r"^(closest|weekday|date|hour|all)$")],
            WEEKDAY: [CallbackQueryHandler(choose_weekday, pattern=r"^[0-6]$")],
            DATE: [MessageHandler(Filters.text & ~Filters.command, input_date)],
            HOUR: [MessageHandler(Filters.text & ~Filters.command, input_hour)],
            CONFIRM: [CallbackQueryHandler(confirm_stage, pattern=r"^(book_now|track_yes|track_no)$")],
            EMAIL: [MessageHandler(Filters.text & ~Filters.command, receive_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    dp.add_handler(reg_conv)
    dp.add_handler(search_conv)
    dp.add_handler(CommandHandler("cancel", cancel))

    # start polling + jobqueue is available via updater.job_queue
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    import re  # used in some functions
    main()
