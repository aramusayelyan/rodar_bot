from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def phone_request_keyboard():
    """Reply keyboard with a single button to share the user's phone number."""
    button = KeyboardButton("📱 Կիսվել հեռախոսահամարով", request_contact=True)
    return ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)

def department_keyboard(departments):
    """
    Inline keyboard for selecting a department.
    `departments` should be a list of tuples (name, value).
    Each button's callback_data is prefixed with "dept:" followed by the value.
    """
    buttons = []
    for name, value in departments:
        buttons.append([InlineKeyboardButton(name, callback_data=f"dept:{value}")])
    # Optionally, you might split into multiple columns if needed.
    return InlineKeyboardMarkup(buttons)

def exam_type_keyboard():
    """Inline keyboard for selecting exam type (theoretical or practical)."""
    buttons = [
        [InlineKeyboardButton("Տեսական", callback_data="theoretical")],
        [InlineKeyboardButton("Գործնական", callback_data="practical")]
    ]
    return InlineKeyboardMarkup(buttons)

def search_method_keyboard():
    """Inline keyboard for selecting search mode: by earliest day, specific date, or specific time."""
    buttons = [
        [InlineKeyboardButton("🔜 Առաջին ազատ օրը", callback_data="day")],
        [InlineKeyboardButton("📅 Ըստ ամսաթվի", callback_data="date")],
        [InlineKeyboardButton("⏰ Ըստ ժամի", callback_data="time")]
    ]
    return InlineKeyboardMarkup(buttons)
