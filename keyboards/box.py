from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from config import BOXES


def generate_delivery_method_kb():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Привезу сам")],
            [KeyboardButton(text="Закажите самовывоз")]
        ],
        resize_keyboard=True
    )
    return keyboard


def generate_delivery_method_for_measurements_kb():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Закажите самовывоз")]
        ],
        resize_keyboard=True
    )
    return keyboard


def generate_boxes_kb():
    buttons = []
    for box in BOXES:
        buttons.append([
            InlineKeyboardButton(
                text=f"{box['name']} - {box['price_per_month']} ₽",
                callback_data=f"select_box_{box['id']}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="Нужны замеры (сделаем при вывозе)",
            callback_data="need_measurements"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def generate_confirm_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Подтвердить выбор", 
                callback_data="confirm_box"),
            InlineKeyboardButton(
                text="К списку боксов", 
                callback_data="back_to_boxes"
            )
        ]
    ])
    return keyboard


def generate_request_contact_kb():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Отправить контакт", 
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard