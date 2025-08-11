from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# Ցուցակը կարճացրել եմ կոճակների համար (անհրաժեշտության դեպքում կարող ես ավելացնել/փոխել ID-երը)
# ID-երը պետք է համապատասխանեն կայքի branchId-երին (օգտագործում ենք հայտնի/հաճախակիները)
BRANCHES = [
    ("Երևան", 33),
    ("Գյումրի", 39),
    ("Վանաձոր", 40),
    ("Աշտարակ", 43),
    ("Արտաշատ (Մխչյան)", 44),
    ("Կապան", 36),
    ("Սևան", 34),
    ("Մարտունի", 35),
    ("Գորիս", 37),
    ("Իջևան", 41),
]

def branch_keyboard() -> InlineKeyboardMarkup:
    btns = [InlineKeyboardButton(name, callback_data=f"branch:{bid}") for name, bid in BRANCHES]
    rows = [btns[i:i+2] for i in range(0, len(btns), 2)]
    return InlineKeyboardMarkup(rows)

# ServiceId-երը՝ տեսական/գործնական (այս ID-երը կայքում օգտագործվում են)
THEORY_ID = 300691
PRACTICE_ID = 300692

def exam_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Տեսական քննություն", callback_data=f"exam:{THEORY_ID}"),
            InlineKeyboardButton("Գործնական քննություն", callback_data=f"exam:{PRACTICE_ID}")
        ]]
    )

def filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Շաբաթվա օրով", callback_data="filter:weekday"),
                InlineKeyboardButton("Ամսաթվով", callback_data="filter:date"),
            ],
            [
                InlineKeyboardButton("Ժամով", callback_data="filter:hour"),
                InlineKeyboardButton("Բոլորը", callback_data="filter:all"),
            ]
        ]
    )

WEEKDAYS = [
    ("Երկուշաբթի", 0),
    ("Երեքշաբթի", 1),
    ("Չորեքշաբթի", 2),
    ("Հինգշաբթի", 3),
    ("Ուրբաթ", 4),
    ("Շաբաթ", 5),
    ("Կիրակի", 6),
]

def weekday_keyboard() -> InlineKeyboardMarkup:
    btns = [InlineKeyboardButton(name, callback_data=f"weekday:{idx}") for name, idx in WEEKDAYS]
    rows = [btns[i:i+2] for i in range(0, len(btns), 2)]
    return InlineKeyboardMarkup(rows)

# /start-ի համար՝ հեռախոսահամար խնդրող ReplyKeyboard
contact_request_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)]],
    one_time_keyboard=True,
    resize_keyboard=True
)
