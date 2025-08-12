# -*- coding: utf-8 -*-
from typing import List, Tuple
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def exam_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Տեսական", "Գործնական"]], resize_keyboard=True, one_time_keyboard=True)

def filter_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        ["Ամենամոտ օր", "Ըստ ամսաթվի"],
        ["Ըստ ժամի", "Շաբաթվա օրով"],
        ["Բոլոր ազատ օրերը"]
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def weekdays_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի"],
        ["Հինգշաբթի", "Ուրբաթ", "Շաբաթ"],
        ["Կիրակի"]
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def list_keyboard_from_pairs(pairs: List[Tuple[str, str]], cols: int = 2) -> ReplyKeyboardMarkup:
    labels = [p[0] for p in pairs]
    rows = [labels[i:i+cols] for i in range(0, len(labels), cols)]
    if not rows:
        rows = [["— ցուցակ դատարկ —"]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def slot_inline_keyboard(slots: List[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for s in slots:
        label = s.get("label") or s.get("time") or s.get("value") or "ժամ"
        value = s.get("value") or label
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"slot|{value}")])
    buttons.append([InlineKeyboardButton("🔔 Միացնել հետևումը", callback_data="follow|on")])
    buttons.append([InlineKeyboardButton("Չեղարկել", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

def confirm_follow_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Միացնել հետևումը", callback_data="follow|on")],
        [InlineKeyboardButton("Չեղարկել", callback_data="cancel")]
    ])

def filter_services_by_exam(services: List[Tuple[str, str]], exam: str) -> List[Tuple[str, str]]:
    if not services:
        return []
    key = "տեսական" if exam == "Տեսական" else "գործնական"
    filtered = [p for p in services if key in p[0].lower()]
    return filtered or services
