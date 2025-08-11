# -*- coding: utf-8 -*-
from typing import List, Tuple
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def phone_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("📱 Ուղարկել հեռախոսահամարս", request_contact=True)]],
                               resize_keyboard=True, one_time_keyboard=True)

def make_menu(rows: List[List[str]]):
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def exam_type_keyboard():
    rows = [["Տեսական", "Գործնական"]]
    return make_menu(rows)

def filter_keyboard():
    rows = [
        ["Ամենամոտ օր"],
        ["Ըստ ամսաթվի", "Ըստ ժամի"],
        ["Շաբաթվա օրով"],
        ["Բոլոր ազատ օրերը"]
    ]
    return make_menu(rows)

def weekdays_keyboard():
    rows = [["Երկուշաբթի","Երեքշաբթի","Չորեքշաբթի"],
            ["Հինգշաբթի","Ուրբաթ","Շաբաթ","Կիրակի"]]
    return make_menu(rows)

def list_keyboard_from_pairs(pairs: List[Tuple[str, str]], cols: int = 2):
    """pairs: [(label, value)] but we show labels to user."""
    labels = [p[0] for p in pairs]
    rows = []
    row = []
    for i, lab in enumerate(labels, 1):
        row.append(lab)
        if i % cols == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return make_menu(rows)

def slot_inline_keyboard(slots: List[dict]):
    # show up to first 8 slots
    btns = []
    for s in slots[:8]:
        t = s.get("label") or s.get("value")
        v = s.get("value")
        btns.append([InlineKeyboardButton(t, callback_data=f"slot|{v}")])
    return InlineKeyboardMarkup(btns)

def confirm_follow_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Սկսել հետևումը", callback_data="follow|on")],
        [InlineKeyboardButton("❌ Չեղարկել", callback_data="cancel")]
    ])
