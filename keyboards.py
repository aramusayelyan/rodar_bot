# -*- coding: utf-8 -*-
from typing import List, Tuple, Sequence
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def exam_type_keyboard() -> ReplyKeyboardMarkup:
    rows = [["Տեսական", "Գործնական"]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def list_keyboard_from_pairs(pairs: Sequence[Tuple[str, str]], cols: int = 2) -> ReplyKeyboardMarkup:
    labels = [lab for lab, _ in pairs]
    rows: List[List[str]] = []
    row: List[str] = []
    for i, lab in enumerate(labels, 1):
        row.append(lab)
        if i % cols == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def filter_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        ["Ամենամոտ օր", "Ըստ ամսաթվի"],
        ["Ըստ ժամի", "Շաբաթվա օրով"],
        ["Բոլոր ազատ օրերը"],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def weekdays_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        ["Երկուշաբթի", "Երեքշաբթի"],
        ["Չորեքշաբթի", "Հինգշաբթի"],
        ["Ուրբաթ", "Շաբաթ", "Կիրակի"],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def slot_inline_keyboard(slots: List[dict]) -> InlineKeyboardMarkup:
    # slots items: {"label": "09:00", "value": "09:00"}
    buttons: List[List[InlineKeyboardButton]] = []
    for s in slots:
        label = s.get("label") or s.get("value") or "—"
        val = s.get("value") or label
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"slot|{val}")])
    # follow/cancel row
    buttons.append(
        [
            InlineKeyboardButton("🔔 Միացնել հետևումը", callback_data="follow|on"),
            InlineKeyboardButton("❌ Չեղարկել", callback_data="cancel"),
        ]
    )
    return InlineKeyboardMarkup(buttons)


def confirm_follow_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔔 Այո, հետևել", callback_data="follow|on")],
            [InlineKeyboardButton("❌ Ոչ, չեղարկել", callback_data="cancel")],
        ]
    )


def filter_services_by_exam(services: List[Tuple[str, str]], exam: str) -> List[Tuple[str, str]]:
    exam = exam.strip()
    if exam == "Տեսական":
        keys = ["տեսական", "theory"]
    else:
        keys = ["գործնական", "practical"]
    out = []
    for lab, val in services:
        low = lab.lower()
        if any(k in low for k in keys):
            out.append((lab, val))
    return out or services
