from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Все заказы", callback_data="admin_orders")],
            [InlineKeyboardButton(text="Добавить промокод", callback_data="add_promo")],
            [InlineKeyboardButton(text="Список промокодов", callback_data="promo_stats")]
        ]
    )
    return keyboard