from telegram import InlineKeyboardButton

# Armenian names of branches (for reply keyboard display)
SECTION_NAMES_ARM = [
    "Երևան", "Շիրակ", "Լոռի", "Արմավիր", "Կոտայք",
    "Արարատ", "Արագածոտն", "Սյունիք (Կապան)", "Տավուշ",
    "Գեղարքունիք (Սևան)", "Գեղարքունիք (Մարտունի)", "Սյունիք (Գորիս)", "Վայոց Ձոր"
]
# Mapping from Armenian name to internal section code (as used in scraper)
SECTION_NAME_TO_CODE = {
    "Երևան": "Yerevan",
    "Շիրակ": "Shirak",
    "Լոռի": "Lori",
    "Արմավիր": "Armavir",
    "Կոտայք": "Kotayk",
    "Արարատ": "Ararat",
    "Արագածոտն": "Aragatsotn",
    "Սյունիք (Կապան)": "Syunik_Kapan",
    "Տավուշ": "Tavush",
    "Գեղարքունիք (Սևան)": "Gegharkunik_Sevan",
    "Գեղարքունիք (Մարտունի)": "Gegharkunik_Martuni",
    "Սյունիք (Գորիս)": "Syunik_Goris",
    "Վայոց Ձոր": "Vayots_Dzor"
}
# Reverse mapping to get Armenian name from code (for output formatting)
SECTION_CODE_TO_ARM = {v: k for k, v in SECTION_NAME_TO_CODE.items()}

# Reply keyboard for section selection (displaying Armenian names)
from telegram import ReplyKeyboardMarkup, KeyboardButton
section_menu = ReplyKeyboardMarkup(
    [[KeyboardButton(name) for name in SECTION_NAMES_ARM[i:i+2]] for i in range(0, len(SECTION_NAMES_ARM), 2)],
    resize_keyboard=True, one_time_keyboard=True
)

# Inline keyboard for exam type selection
exam_type_buttons = [
    [InlineKeyboardButton("Տեսություն 📘", callback_data="type_theory"),
     InlineKeyboardButton("Գործնական 🚗", callback_data="type_practical")]
]

# Inline keyboard for filter type selection
filter_type_buttons = [
    [InlineKeyboardButton("Շաբաթվա օրով", callback_data="filter_day"),
     InlineKeyboardButton("Օրացուցային ամսաթվով", callback_data="filter_date")],
    [InlineKeyboardButton("Ժամով", callback_data="filter_hour"),
     InlineKeyboardButton("Առանց ֆիլտրի", callback_data="filter_none")]
]

# Inline keyboard for weekday selection
weekday_buttons = [
    [InlineKeyboardButton("Երկուշաբթի", callback_data="day_0"),
     InlineKeyboardButton("Երեքշաբթի", callback_data="day_1"),
     InlineKeyboardButton("Չորեքշաբթի", callback_data="day_2")],
    [InlineKeyboardButton("Հինգշաբթի", callback_data="day_3"),
     InlineKeyboardButton("Ուրբաթ", callback_data="day_4")],
    [InlineKeyboardButton("Շաբաթ", callback_data="day_5"),
     InlineKeyboardButton("Կիրակի", callback_data="day_6")]
]
