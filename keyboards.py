from telegram import ReplyKeyboardMarkup

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["Երևան", "Գյումրի"], ["Վանաձոր", "Արտաշատ"]],
        resize_keyboard=True
    )

def exam_type_keyboard():
    return ReplyKeyboardMarkup(
        [["Տեսական", "Գործնական"]],
        resize_keyboard=True
    )

def service_keyboard():
    return ReplyKeyboardMarkup(
        [["Ազատ օրեր", "Ըստ ամսաթվի"], ["Ըստ ժամի"]],
        resize_keyboard=True
    )
