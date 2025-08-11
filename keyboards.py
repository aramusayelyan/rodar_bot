# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Define Armenian text options for the bot's interactive menus

# Service (operation) options: list of tuples (label, service_id)
SERVICE_OPTIONS = [
    ("Տեսական քննություն (նոր վարորդական)", "300691"),
    ("Գործնական քննություն (նոր վարորդական)", "300692"),
    ("Տեսական քննություն (D/D1 կարգ)", "300695"),
    ("Գործնական քննություն (D/D1 կարգ)", "300696"),
    ("Գործնական քննություն (A/B/C/E կարգեր)", "300697"),
    ("Վկայականի փոխանակում (կորած ներառյալ)", "300693"),
    ("Հին վկայականի փոխանակում (նորով)", "300694"),
    ("ՏՄ գրանցում (զննություն պահանջող)", "300698"),
    ("ՏՄ գրանցում (առանց զննության)", "300700")
]

# Branch options: list of tuples (label, branch_id)
BRANCH_OPTIONS = [
    ("Երևան", "33"),
    ("Գյումրի (Շիրակ)", "39"),
    ("Վանաձոր (Լոռի)", "40"),
    ("Մեծամոր (Արմավիր)", "38"),
    ("Ակունք (Կոտայք)", "42"),
    ("Մխչյան (Արարատ)", "44"),
    ("Աշտարակ (Արագածոտն)", "43"),
    ("Կապան (Սյունիք)", "36"),
    ("Իջևան (Տավուշ)", "41"),
    ("Սևան (Գեղարքունիք)", "34"),
    ("Մարտունի (Գեղարքունիք)", "35"),
    ("Գորիս (Սյունիք)", "37"),
    ("Եղեգնաձոր (Վայոց ձոր)", "45")
]

# Filter criteria options
FILTER_OPTIONS = [
    ("Ամենամոտ ազատ օրը", "closest"),
    ("Շաբաթվա օրով որոնում", "weekday"),
    ("Ըստ ամսաթվի որոնում", "date"),
    ("Ըստ ժամի որոնում", "hour"),
    ("Բոլոր հասանելի օրերը", "all")
]

# Weekday options (Armenian weekdays, Monday=0)
WEEKDAY_OPTIONS = [
    ("Երկուշաբթի", "0"),
    ("Երեքշաբթի", "1"),
    ("Չորեքշաբթի", "2"),
    ("Հինգշաբթի", "3"),
    ("Ուրբաթ", "4"),
    ("Շաբաթ", "5"),
    ("Կիրակի", "6")
]

def build_menu(options, n_cols=1):
    """Utility to build an inline keyboard from options list of (label, data) pairs."""
    buttons = [InlineKeyboardButton(text=label, callback_data=data) for label, data in options]
    # split list into columns
    menu = [buttons[i:i+n_cols] for i in range(0, len(buttons), n_cols)]
    return InlineKeyboardMarkup(menu)
