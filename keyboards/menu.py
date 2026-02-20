from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="О нас"),
                KeyboardButton(text="Профиль"),
                KeyboardButton(text="Мои заказы")
            ],
            [
                KeyboardButton(text="Правила хранения"),
                KeyboardButton(text="Арендовать бокс")
            ],
        ],
        resize_keyboard=True,
    )