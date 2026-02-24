from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import MANAGER_TG_ID


def main_menu_kb(user_id: int):
    keyboard=[
        [
            KeyboardButton(text="О нас"),
            KeyboardButton(text="Список вещей"),
            KeyboardButton(text="Мои заказы")
        ],
        [
            KeyboardButton(text="Правила хранения"),
            KeyboardButton(text="Арендовать бокс")
        ],
    ]
    if user_id in MANAGER_TG_ID:
        keyboard.append([KeyboardButton(text="Админ-панель")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
