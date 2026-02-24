from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)


def generate_rules():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Помощь по утилизации", callback_data="dispose_help")]
    ])
    return keyboard


def generate_prohibited_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Связаться с оператором", callback_data="contact_operator")]
    ])
    return keyboard