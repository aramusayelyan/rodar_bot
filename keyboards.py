from telegram import ReplyKeyboardMarkup, KeyboardButton

# Keyboard for requesting phone contact
phone_request_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True
)

# Keyboard for exam type selection
exam_type_keyboard = ReplyKeyboardMarkup(
    [["Տեսական", "Գործնական"]],
    resize_keyboard=True, one_time_keyboard=True
)

# List of branch options (static list of typical exam centers in Armenia)
branch_options = [
    "Երևան",
    "Շիրակ (Գյումրի)",
    "Լոռի (Վանաձոր)",
    "Արմավիր (Մեծամոր)",
    "Կոտայք (Աբովյան)",
    "Արարատ (Մասիս)",
    "Արագածոտն (Աշտարակ)",
    "Սյունիք (Կապան)",
    "Սյունիք (Գորիս)",
    "Տավուշ (Իջևան)",
    "Գեղարքունիք (Սևան)",
    "Գեղարքունիք (Մարտունի)",
    "Վայոց Ձոր (Եղեգնաձոր)"
]
# Construct reply keyboard for branches (split into rows for better layout)
branch_keyboard = ReplyKeyboardMarkup(
    [
        ["Երևան", "Շիրակ (Գյումրի)", "Լոռի (Վանաձոր)"],
        ["Արմավիր (Մեծամոր)", "Կոտայք (Աբովյան)", "Արարատ (Մասիս)"],
        ["Արագածոտն (Աշտարակ)", "Սյունիք (Կապան)", "Սյունիք (Գորիս)", "Տավուշ (Իջևան)"],
        ["Գեղարքունիք (Սևան)", "Գեղարքունիք (Մարտունի)", "Վայոց Ձոր (Եղեգնաձոր)"]
    ],
    resize_keyboard=True, one_time_keyboard=True
)

# Keyboard for filter type selection
filter_type_keyboard = ReplyKeyboardMarkup(
    [["Ժամով", "Ամսաթվով"], ["Շաբաթվա օրով", "Ամբողջը"]],
    resize_keyboard=True, one_time_keyboard=True
)
