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
            [KeyboardButton(text="Закажите вывоз")]
        ],
        resize_keyboard=True
    )
    return keyboard


def generate_volume_kb():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Маленький")],
            [KeyboardButton(text="Средний")],
            [KeyboardButton(text="Большой")],
            [KeyboardButton(text="Отправить список")],
            [KeyboardButton(text="Отправить фото")]
        ],
        resize_keyboard=True
    )
    return keyboard


def generate_boxes_kb():
    buttons = []
    for box in BOXES:
        buttons.append([
            InlineKeyboardButton(
                text=f"{box['name']} - {box['size']}",
                callback_data=f"select_box_{box['id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_delivery")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def generate_confirm_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выбрать этот бокс", callback_data="confirm_box"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_boxes")
        ]
    ])
    return keyboard


def generate_location_kb():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],

        ],
        resize_keyboard=True
    )
    return keyboard