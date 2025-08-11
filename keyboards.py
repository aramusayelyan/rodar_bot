from telegram import ReplyKeyboardMarkup, KeyboardButton

# Ստեղծել contact request կոճակով ստեղնաշար հեռախոսահամար ստանալու համար
def phone_request_keyboard():
    # Կոճակ, որը ուղարկում է օգտատիրոջ կոնտակտը (հեռախոսահամարը) սեղմելիս
    button = KeyboardButton("📱 Ուղարկել հեռախոսահամարը", request_contact=True)  # :contentReference[oaicite:18]{index=18}
    return ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)

# Ստորաբաժանման (բաժնի) ընտրության ստեղնաշար կազմող ֆունկցիա
def branch_keyboard():
    branches = [
        "Երևանի հաշվառման-քննական բաժին",
        "Գյումրիի հսկիչ-քննական կենտրոն",
        "Վանաձորի հաշվառման-քննական բաժանմունք",
        "Արմավիրի հաշվառման-քննական բաժանմունք",
        "Կոտայքի հաշվառման-քննական բաժանմունք",
        "Արտաշատի հաշվառման-քննարկման բաժանմունք",
        "Աշտարակի հաշվառման-քննարկման բաժանմունք",
        "Կապանի հաշվառման-քննարկման բաժանմունք",
        "Իջևանի հաշվառման-քննարկման բաժանմունք",
        "Սևանի հաշվառման-քննարկման բաժանմունք",
        "Մարտունու հաշվառման-քննարկման խումբ",
        "Գորիսի հաշվառման-քննարկման խումբ",
        "Վայքի հաշվառման-քննարկման խումբ"
    ]
    # Քանի որ ցանկը երկար է, ձևավորում ենք ստեղնաշարը 2 սյունակով՝ ավելի կոմպակտ
    keyboard_layout = []
    for i in range(0, len(branches), 2):
        if i+1 < len(branches):
            keyboard_layout.append([branches[i], branches[i+1]])
        else:
            keyboard_layout.append([branches[i]])
    return ReplyKeyboardMarkup(keyboard_layout, one_time_keyboard=True, resize_keyboard=True)

# Քննության տեսակի ընտրության ստեղնաշար
def exam_type_keyboard():
    # Առաջարկում ենք 4 տարբերակ՝ համապատասխանում է կայքի radio button-ներին
    options = [
        ["Տեսական քննություն", "Գործնական քննություն"],
        ["Վար. վկայականի Փոխարինում", "Վար. վկայականի Կորուստ"]
    ]
    # Նշում: "Վար. վկայականի" նախաբանը կտոցեցինք, որպեսզի կոճակների վրայի տեքստը շատ երկար չստացվի։
    # Օգտատիրոջը հասկանալի է, որ Փոխարինում/Կորուստ նկատի ունի վարորդական վկայականի։
    return ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)
