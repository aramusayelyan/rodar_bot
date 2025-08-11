from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# Define branches (exam centers) with their IDs and display names.
# The branch names are in Armenian and are kept short (city or region) for buttons.
BRANCHES = [
    ("Երևան", 33),
    ("Գյումրի", 39),
    ("Վանաձոր", 40),
    ("Մեծամոր", 38),       # Armavir region
    ("Ակունք (Կոտայք)", 42),
    ("Մխչյան", 44),       # Ararat region
    ("Աշտարակ", 43),      # Aragatsotn region
    ("Կապան", 36),        # Syunik region
    ("Իջևան", 41),        # Tavush region
    ("Սևան", 34),         # Gegharkunik region
    ("Մարտունի", 35),     # Gegharkunik region
    ("Գորիս", 37),        # Syunik region
    ("Եղեգնաձոր", 45)     # Vayots Dzor region
]

def branch_keyboard():
    """Creates an inline keyboard for branch selection."""
    buttons = []
    # Arrange buttons in 2 per row for neat display
    for name, branch_id in BRANCHES:
        buttons.append(InlineKeyboardButton(name, callback_data=f"branch:{branch_id}"))
    # Split the flat list into rows of 2 buttons
    keyboard_rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(keyboard_rows)

# Exam types (the main two exam types of interest with their service IDs)
EXAM_TYPES = [
    ("Տեսական", 300691),    # Theoretical exam:contentReference[oaicite:2]{index=2}
    ("Գործնական", 300692)   # Practical exam:contentReference[oaicite:3]{index=3}
]

def exam_keyboard():
    """Inline keyboard for exam type selection."""
    buttons = [
        InlineKeyboardButton("Տեսական քննություն", callback_data=f"exam:{300691}"),
        InlineKeyboardButton("Գործնական քննություն", callback_data=f"exam:{300692}")
    ]
    keyboard = [[buttons[0], buttons[1]]]  # put two buttons in one row
    return InlineKeyboardMarkup(keyboard)

def filter_keyboard():
    """Inline keyboard for filter options."""
    buttons = [
        InlineKeyboardButton("Շաբաթվա օրով", callback_data="filter:weekday"),
        InlineKeyboardButton("Ամսաթվով", callback_data="filter:date"),
        InlineKeyboardButton("Ժամով", callback_data="filter:hour"),
        InlineKeyboardButton("Բոլորը", callback_data="filter:all")
    ]
    # We can arrange these in two rows for better spacing
    keyboard = [[buttons[0], buttons[1]], [buttons[2], buttons[3]]]
    return InlineKeyboardMarkup(keyboard)

# Weekday selection keyboard (Armenian full weekday names)
WEEKDAYS = [
    ("Երկուշաբթի", 0),   # Monday (0 if we use Python's weekday numbering where Mon=0)
    ("Երեքշաբթի", 1),   # Tuesday
    ("Չորեքշաբթի", 2),  # Wednesday
    ("Հինգշաբթի", 3),   # Thursday
    ("Ուրբաթ", 4),       # Friday
    ("Շաբաթ", 5),       # Saturday
    ("Կիրակի", 6)        # Sunday
]

def weekday_keyboard():
    """Inline keyboard for weekday selection (for filter by weekday)."""
    buttons = []
    for name, day_index in WEEKDAYS:
        buttons.append(InlineKeyboardButton(name, callback_data=f"weekday:{day_index}"))
    # Arrange in rows (e.g., 2 per row for readability)
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(keyboard)

# Additionally, a reply keyboard for requesting contact (phone number) on /start
contact_request_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)]],
    one_time_keyboard=True,
    resize_keyboard=True
)
