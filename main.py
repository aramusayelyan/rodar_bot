#!/usr/bin/env python3
import asyncio
import logging
import os
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

import config
import keyboards as kb
import scraper
import database as db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# Conversation states
S_PHONE, S_PSN, S_SMS, S_SEARCH_EXAM, S_SEARCH_SERVICE, S_SEARCH_BRANCH, S_FILTER, S_DATE, S_HOUR, S_EMAIL = range(10)

# In-memory per-user working objects
USER_SESS = {}  # tg_id -> requests.Session
USER_CTX = {}   # tg_id -> dict temp state

def _get_session_for_user(tg_id: int):
    sess = USER_SESS.get(tg_id)
    if sess is None:
        row = db.get_user(tg_id)
        cookies = row.get("cookies") if row else None
        sess = scraper._new_session(cookies=cookies)
        USER_SESS[tg_id] = sess
    return sess

def _save_cookies(tg_id: int):
    sess = USER_SESS.get(tg_id)
    if not sess:
        return
    ck = scraper._serialize_cookies(sess)
    db.update_cookies(tg_id, ck)

def norm_phone_for_login(user_input: str) -> str:
    # keep local part for API (without +374 / leading 0)
    return scraper.normalize_phone_to_local(user_input)

def _fmt_services_by_exam(services, exam_text):
    # filter by text contains
    key = "տեսակ"  # loose
    ex = exam_text.strip()
    out = []
    for s in services:
        t = s["label"].lower()
        if ex == "Տեսական" and ("տեսական" in t):
            out.append(s)
        elif ex == "Գործնական" and ("գործնական" in t):
            out.append(s)
    # if filter got empty -> fall back to all
    return out or services

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    USER_CTX[tg_id] = {}
    await update.message.reply_text(
        "Բարի գալուստ։ Խնդրում եմ ուղարկել ձեր հեռախոսահամարը՝ "
        "ֆորմատով +374XXXXXXXX կամ 0XXXXXXXX։",
        reply_markup=kb.phone_keyboard()
    )
    return S_PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if update.message.contact and update.message.contact.phone_number:
        raw = update.message.contact.phone_number
    else:
        raw = (update.message.text or "").strip()
    local = norm_phone_for_login(raw)
    if not local.isdigit() or not (8 <= len(local) <= 9):
        await update.message.reply_text("Խնդրում եմ ուղարկել ճիշտ հեռախոսահամար։ Օրինակ՝ +37499123456 կամ 099123456")
        return S_PHONE
    USER_CTX[tg_id]["phone_local"] = local
    await update.message.reply_text("Մուտքագրեք ձեր հանրային ծառայության համարանիշը (ՀԾՀ, 10 թվանշան):")
    return S_PSN

async def psn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    psn = (update.message.text or "").strip()
    if not psn.isdigit() or len(psn) != 10:
        await update.message.reply_text("ՀԾՀ-ն պետք է լինի 10 թվանշան, փորձեք կրկին։")
        return S_PSN
    USER_CTX[tg_id]["psn"] = psn

    # upsert minimal in DB
    db.upsert_user(tg_id, phone=USER_CTX[tg_id]["phone_local"], social=psn)

    # try to pre-load csrf & session
    sess = _get_session_for_user(tg_id)
    scraper._load_csrf(sess)

    await update.message.reply_text(
        "Շնորհակալություն։ Կարող եք սկսել որոնումը՝ /search հրամանով։\n"
        "Եթե կայքը պահանջի մուտք՝ կուղարկեմ հ_prompt SMS հաստատման համար։"
    )
    return ConversationHandler.END

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    # ensure we can fetch services/branches (if fails -> start login)
    sess = _get_session_for_user(tg_id)
    try:
        services, branches = scraper.fetch_services_branches(sess)
        if not services or not branches:
            raise RuntimeError("empty lists")
        USER_CTX.setdefault(tg_id, {})["services"] = services
        USER_CTX[tg_id]["branches"] = branches
        await update.message.reply_text("Ընտրեք քննության տեսակը։", reply_markup=kb.exam_type_keyboard())
        return S_SEARCH_EXAM
    except Exception:
        # start login (SMS)
        phone = USER_CTX.get(tg_id, {}).get("phone_local")
        psn = USER_CTX.get(tg_id, {}).get("psn")
        if not phone or not psn:
            await update.message.reply_text("Սկզբում կատարեք /start՝ հեռախոս + ՀԾՀ։")
            return ConversationHandler.END
        try:
            scraper.login_init(sess, psn=psn, phone=phone, country="AM")
            await update.message.reply_text("✅ SMS կոդը ուղարկվեց։ Խնդրում եմ ուղարկել ստացված 6-անիշ կոդը։")
            return S_SMS
        except Exception as e:
            log.error("login_init failed: %s", e, exc_info=True)
            await update.message.reply_text("Չհաջողվեց մուտք գործել։ Փորձեք կրկին /search կամ փոքր-ինչ ուշ։")
            return ConversationHandler.END

async def sms_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    code = (update.message.text or "").strip()
    if not code.isdigit() or not (4 <= len(code) <= 8):
        await update.message.reply_text("Կոդը թվերից է կազմված։ Ուղարկեք կրկին։")
        return S_SMS
    phone = USER_CTX[tg_id]["phone_local"]
    psn = USER_CTX[tg_id]["psn"]
    sess = _get_session_for_user(tg_id)
    try:
        scraper.login_verify(sess, psn=psn, phone=phone, token=code, country="AM")
        _save_cookies(tg_id)
        await update.message.reply_text("✅ Մուտքը հաջողվեց։ Շարունակենք որոնումը։ Ընտրեք քննության տեսակը։", reply_markup=kb.exam_type_keyboard())
        # refill lists after login
        services, branches = scraper.fetch_services_branches(sess)
        USER_CTX[tg_id]["services"] = services
        USER_CTX[tg_id]["branches"] = branches
        return S_SEARCH_EXAM
    except Exception as e:
        log.error("login_verify failed: %s", e, exc_info=True)
        await update.message.reply_text("Սխալ SMS կամ ժամկետանց։ Փորձեք նորից /search և կրկնել մուտքը։")
        return ConversationHandler.END

async def pick_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    ex = (update.message.text or "").strip()
    if ex not in ("Տեսական", "Գործնական"):
        await update.message.reply_text("Ընտրեք՝ «Տեսական» կամ «Գործնական»։")
        return S_SEARCH_EXAM
    USER_CTX[tg_id]["exam"] = ex

    services = USER_CTX[tg_id].get("services", [])
    filtered = _fmt_services_by_exam(services, ex)
    USER_CTX[tg_id]["services_filtered"] = filtered

    await update.message.reply_text("Ընտրեք ծառայությունը․", reply_markup=kb.list_to_keyboard([s["label"] for s in filtered], row=1))
    return S_SEARCH_SERVICE

async def pick_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    label = (update.message.text or "").strip()
    items = USER_CTX[tg_id].get("services_filtered", [])
    match = next((s for s in items if s["label"] == label), None)
    if not match:
        await update.message.reply_text("Խնդրում եմ ընտրել ցուցակից։")
        return S_SEARCH_SERVICE
    USER_CTX[tg_id]["service"] = match

    branches = USER_CTX[tg_id].get("branches", [])
    await update.message.reply_text("Ընտրեք բաժանմունքը․", reply_markup=kb.list_to_keyboard([b["label"] for b in branches], row=1))
    return S_SEARCH_BRANCH

async def pick_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    label = (update.message.text or "").strip()
    branches = USER_CTX[tg_id].get("branches", [])
    match = next((b for b in branches if b["label"] == label), None)
    if not match:
        await update.message.reply_text("Խնդրում եմ ընտրել ցուցակից։")
        return S_SEARCH_BRANCH
    USER_CTX[tg_id]["branch"] = match
    await update.message.reply_text("Ընտրեք ազատ օրերի ֆիլտրի տարբերակը․", reply_markup=kb.filter_keyboard())
    return S_FILTER

def _today_str():
    return datetime.now().strftime("%d-%m-%Y")

async def pick_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    choice = (update.message.text or "").strip()
    svc = USER_CTX[tg_id]["service"]["id"]
    br = USER_CTX[tg_id]["branch"]["id"]
    sess = _get_session_for_user(tg_id)

    if choice == "Ամենամոտ օրը":
        data = scraper.nearest_day(sess, br, svc, _today_str())
        if not data:
            await update.message.reply_text("Ազատ մոտ օր ներկայումս չգտնվեց։ Փորձեք այլ ֆիլտր։")
            return S_FILTER
        USER_CTX[tg_id]["picked_day"] = data["day"]
        USER_CTX[tg_id]["day_slots"] = data["slots"]
        await update.message.reply_text(f"Մոտակա օր՝ {data['day']}. Ընտրեք ժամը։", reply_markup=None)
        await update.message.reply_text("Սեղմեք ցանկալի ժամը․", reply_markup=kb.inline_slots_kb(data["slots"]))
        return S_HOUR

    elif choice == "Ըստ ամսաթվի":
        await update.message.reply_text("Մուտքագրեք ամսաթիվը՝ ՕՕ-ԱԱ-ԹԹԹԹ (օր. 25-08-2025)")
        return S_DATE

    elif choice == "Ըստ ժամի":
        await update.message.reply_text("Մուտքագրեք ժամը՝ ԺԺ:ՐՐ (օր. 10:00)")
        return S_HOUR

    elif choice == "Շաբաթվա օրով":
        await update.message.reply_text("Մուտքագրեք շաբաթվա օրը (Երկուշաբթի ... Կիրակի) — այս տարբերակը այժմ հասանելի կլինի հաջորդ թարմացման մեջ։")
        return S_FILTER

    elif choice == "Բոլոր ազատ օրերը":
        # heuristics: bring days of current month that are not disabled and have slots
        day0 = _today_str()
        disabled = scraper.slots_for_month(sess, br, svc, day0)
        # Build readable info
        await update.message.reply_text("Խնդրում ենք ընտրել կոնկրետ ամսաթիվ «Ըստ ամսաթվի» տարբերակով՝ տեսնելու ժամերը։")
        return S_FILTER

    else:
        await update.message.reply_text("Ընտրեք մատչելի տարբերակներից։")
        return S_FILTER

async def input_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    txt = (update.message.text or "").strip()
    try:
        datetime.strptime(txt, "%d-%m-%Y")
    except Exception:
        await update.message.reply_text("Ֆորմատը պետք է լինի ՕՕ-ԱԱ-ԹԹԹԹ (օր. 05-10-2025)")
        return S_DATE
    USER_CTX[tg_id]["picked_day"] = txt
    sess = _get_session_for_user(tg_id)
    svc = USER_CTX[tg_id]["service"]["id"]
    br = USER_CTX[tg_id]["branch"]["id"]
    try:
        slots = scraper.slots_for_day(sess, br, svc, txt)
        if not slots:
            await update.message.reply_text("Այդ ամսաթվով ազատ ժամեր չկան։ Փորձեք այլ օր։")
            return S_FILTER
        USER_CTX[tg_id]["day_slots"] = slots
        await update.message.reply_text("Ընտրեք ժամը․", reply_markup=kb.inline_slots_kb(slots))
        return S_HOUR
    except Exception as e:
        log.error("slots_for_day failed: %s", e, exc_info=True)
        await update.message.reply_text("Չհաջողվեց բերել տվյալ օրը։ Փորձեք կրկին։")
        return S_FILTER

async def input_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # only used when user typed HH:MM (not via callback)
    tg_id = update.effective_user.id
    txt = (update.message.text or "").strip()
    if not (len(txt) == 5 and txt[2] == ":" and txt[:2].isdigit() and txt[3:].isdigit()):
        await update.message.reply_text("Ժամի ֆորմատը՝ ԺԺ:ՐՐ (օր. 09:30)")
        return S_HOUR
    USER_CTX[tg_id]["picked_hour"] = txt
    await update.message.reply_text("Մուտքագրեք ձեր email-ը՝ ամրագրումն ավարտելու համար։")
    return S_EMAIL

async def cb_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("slot|"):
        return
    val = data.split("|", 1)[1]
    USER_CTX.setdefault(tg_id, {})["picked_hour"] = val
    await q.message.reply_text("Մուտքագրեք ձեր email-ը՝ ամրագրումն ավարտելու համար։")
    return S_EMAIL

async def input_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    email = (update.message.text or "").strip()
    if "@" not in email or "." not in email:
        await update.message.reply_text("Email-ն սխալ է։ Փորձեք կրկին։")
        return S_EMAIL

    sess = _get_session_for_user(tg_id)
    svc = USER_CTX[tg_id]["service"]["id"]
    br = USER_CTX[tg_id]["branch"]["id"]
    day = USER_CTX[tg_id]["picked_day"]
    hour = USER_CTX[tg_id]["picked_hour"]

    try:
        res = scraper.register_appointment(sess, br, svc, day, hour, email)
        _save_cookies(tg_id)
        pin = res.get("pin", "—")
        await update.message.reply_text(f"✅ Ամրագրումը հաջողվեց։ PIN՝ {pin}")
    except Exception as e:
        log.error("register failed: %s", e, exc_info=True)
        await update.message.reply_text("Չհաջողվեց ամրագրել։ Հնարավոր է՝ սեսիան ժամկետանց է կամ ժամը զբաղված է։ Փորձեք կրկին /search։")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Գործընթացը դադարեցվեց։")
    return ConversationHandler.END

def build_app() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env variable is required")

    application = Application.builder().token(config.BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            S_PHONE: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), phone)],
            S_PSN: [MessageHandler(filters.TEXT & ~filters.COMMAND, psn)],
            S_SMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sms_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="start_conv",
        persistent=False,
    )

    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", cmd_search)],
        states={
            S_SMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sms_code)],
            S_SEARCH_EXAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, pick_exam)],
            S_SEARCH_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pick_service)],
            S_SEARCH_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, pick_branch)],
            S_FILTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, pick_filter)],
            S_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_date)],
            S_HOUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_hour)],
            S_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="search_conv",
        persistent=False,
    )

    application.add_handler(conv)
    application.add_handler(search_conv)
    application.add_handler(CallbackQueryHandler(cb_slot, pattern=r"^slot\|"))

    return application

def main():
    log.info("Starting bot (webhook mode)…")
    app = build_app()
    if not config.WEBHOOK_BASE_URL:
        raise RuntimeError("WEBHOOK_BASE_URL env var is required on Render")

    webhook_path = f"/bot{config.BOT_TOKEN}"
    url = f"{config.WEBHOOK_BASE_URL}{webhook_path}"
    app.run_webhook(
        listen="0.0.0.0",
        port=config.PORT,
        url=url,
        webhook_path=webhook_path,
        secret_token=None,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
