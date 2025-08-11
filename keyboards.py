# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Exam types (services) — IDs may vary on the site; adjust if needed
SERVICES = [
    ("Տեսական քննություն", "300691"),
    ("Գործնական քննություն", "300692"),
]

FILTERS = [
    ("Ամենամոտ օր", "closest"),
    ("Շաբաթվա օրով", "weekday"),
    ("Ըստ ամսաթվի", "date"),
    ("Ըստ ժամի", "hour"),
    ("Բոլոր ազատ օրերը", "all"),
]

WEEKDAYS = [
    ("Երկուշաբթի", "0"),
    ("Երեքշաբթի", "1"),
    ("Չորեքշաբթի", "2"),
    ("Հինգշաբթի", "3"),
    ("Ուրբաթ", "4"),
    ("Շաբաթ", "5"),
    ("Կիրակի", "6"),
]

def build_inline(options, cols=1):
    buttons = [InlineKeyboardButton(text=label, callback_data=data) for (label, data) in options]
    rows = [buttons[i:i+cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)
