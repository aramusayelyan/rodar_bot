from telegram import ReplyKeyboardMarkup

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["Երևան", "Գյումրի"], ["Վանաձոր", "Արտաշատ"]],
        one_time_keyboard=True, resize_keyboard=True
    )

def exam_type_keyboard():
    return ReplyKeyboardMarkup(
        [["Տեսական", "Գործնական"]],
        one_time_keyboard=True, resize_keyboard=True
    )

def service_keyboard():
    return ReplyKeyboardMarkup(
        [["Առաջիկա ազատ օր", "Ըստ ամսաթվի"], ["Ըստ ժամի"]],
        one_time_keyboard=True, resize_keyboard=True
    )
