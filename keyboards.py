from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def rows(items, per_row=2):
    return [items[i:i+per_row] for i in range(0, len(items), per_row)]

def phone_request_kb():
    return ReplyKeyboardMarkup(
        [[{"text": "📱 Ուղարկել հեռախոսահամարս", "request_contact": True}]],
        resize_keyboard=True, one_time_keyboard=True
    )

def ok_cancel_kb(ok_text="Շարունակել", cancel_text="Չեղարկել"):
    return ReplyKeyboardMarkup([[ok_text, cancel_text]], resize_keyboard=True, one_time_keyboard=True)

def services_kb(services):
    # services: list of (id,label)
    buttons = [[s[1]] for s in services]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

def branches_kb(branches):
    # branches: list of (id,label)
    buttons = [[b[1]] for b in branches]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

def exam_type_kb():
    return ReplyKeyboardMarkup(
        [["Տեսական", "Գործնական"], ["Բոլոր ծառայությունները"]],
        resize_keyboard=True, one_time_keyboard=True
    )

def filter_kb():
    return ReplyKeyboardMarkup(
        [["Ամենամոտ օրը", "Բոլոր ազատ օրերը"],
         ["Ֆիլտր՝ շաբաթվա օրով", "Ֆիլտր՝ ամսաթվով"],
         ["Ֆիլտր՝ ժամով"]],
        resize_keyboard=True, one_time_keyboard=True
    )

def weekdays_kb():
    return ReplyKeyboardMarkup(
        [["Երկուշաբթի", "Երեքշաբթի"],
         ["Չորեքշաբթի", "Հինգշաբթի"],
         ["Ուրբաթ", "Շաբաթ", "Կիրակի"]],
        resize_keyboard=True, one_time_keyboard=True
    )

def times_kb(slots):
    # slots: list of dicts with "label" / "value"
    labels = [s.get("label") or s.get("value") for s in slots]
    return ReplyKeyboardMarkup(rows(labels, per_row=3), resize_keyboard=True, one_time_keyboard=True)

def yes_no_kb():
    return ReplyKeyboardMarkup([["Այո", "Ոչ"]], resize_keyboard=True, one_time_keyboard=True)
