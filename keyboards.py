from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Ուղարկել հեռախոսահամարս", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def exam_type_keyboard():
    return ReplyKeyboardMarkup(
        [["Տեսական", "Գործնական"]],
        resize_keyboard=True, one_time_keyboard=True
    )

def filter_keyboard():
    return ReplyKeyboardMarkup(
        [["Ամենամոտ օրը"], ["Ըստ ամսաթվի"], ["Ըստ ժամի"], ["Շաբաթվա օրով"], ["Բոլոր ազատ օրերը"]],
        resize_keyboard=True, one_time_keyboard=True
    )

def yes_no_keyboard():
    return ReplyKeyboardMarkup([["Այո", "Ոչ"]], resize_keyboard=True, one_time_keyboard=True)

def list_to_keyboard(items, row=2):
    rows, cur = [], []
    for txt in items:
        cur.append(txt)
        if len(cur) == row:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def inline_slots_kb(slots):
    # slots: list of {'value': '10:00', 'label': '10:00'}
    buttons = [[InlineKeyboardButton(s["label"], callback_data=f"slot|{s['value']}")] for s in slots]
    return InlineKeyboardMarkup(buttons)
