from telegram import ReplyKeyboardMarkup, KeyboardButton

# Branch options (list of lists for keyboard rows)
branch_options = [
    ["Երևանի հաշվառման-քննական բաժին"],
    ["Գյումրիի հաշվառման-քննական կենտրոն", "Վանաձորի հաշվառման-քննական բաժին"],
    ["Արմավիրի հաշվառման-քննական բաժին", "Աշտարակի հաշվառման-քննական բաժին"],
    ["Կոտայքի հաշվառման-քննական բաժին", "Արտաշատի հաշվառման-քննական բաժին"],
    ["Մարտունիի հաշվառման-քննական բաժին", "Սևանի հաշվառման-քննական բաժին"],
    ["Կապանի հաշվառման-քննական բաժին", "Գորիսի հաշվառման-քննական բաժին"],
    ["Իջևանի հաշվառման-քննական բաժին", "Վայքի հաշվառման-քննական բաժին"]
]
branch_markup = ReplyKeyboardMarkup(branch_options, one_time_keyboard=True, resize_keyboard=True)

# Exam type options
exam_type_options = [["Տեսական քննություն", "Գործնական քննություն"]]
exam_type_markup = ReplyKeyboardMarkup(exam_type_options, one_time_keyboard=True, resize_keyboard=True)

# Filter method options
filter_method_options = [
    ["Բոլոր ամսաթվերը", "Ըստ շաբաթվա օրվա"],
    ["Ըստ ամսաթվի", "Ըստ ժամի"]
]
filter_method_markup = ReplyKeyboardMarkup(filter_method_options, one_time_keyboard=True, resize_keyboard=True)

# Weekdays options (Armenian names)
weekdays_options = [
    ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի"],
    ["Ուրբաթ", "Շաբաթ", "Կիրակի"]
]
weekdays_markup = ReplyKeyboardMarkup(weekdays_options, one_time_keyboard=True, resize_keyboard=True)
