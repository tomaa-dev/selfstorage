from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)


def items_list_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Забрать вещи",
                    callback_data=f"pickup_full_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Забрать часть вещей",
                    callback_data=f"pickup_partial_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Заказать доставку",
                    callback_data=f"pickup_delivery_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Продлить аренду",
                    callback_data=f"extend_order_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Связаться с менеджером",
                    callback_data="contact_manager"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Вернуться в меню",
                    callback_data="back_to_main"
                )
            ]
        ]
    )


def extend_period_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="1 месяц",
                    callback_data=f"extend_1_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="3 месяца",
                    callback_data=f"extend_3_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="6 месяцев",
                    callback_data=f"extend_6_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=f"back_to_items_{order_id}"
                )
            ]
        ]
    )


def confirm_extend_kb(order_id: int, months: int, price: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтвердить",
                    callback_data=f"confirm_extend_{order_id}_{months}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"cancel_extend_{order_id}"
                )
            ]
        ]
    )


def item_details_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Описание содержимого",
                    callback_data=f"item_desc_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Размер бокса",
                    callback_data=f"item_size_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Даты хранения",
                    callback_data=f"item_dates_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="История оплат",
                    callback_data=f"item_payments_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к списку",
                    callback_data="back_to_items_list"
                )
            ]
        ]
    )


def storage_info_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Как подготовить вещи",
                    callback_data="storage_prepare"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Доставка и самовывоз",
                    callback_data="storage_delivery"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Безопасность хранения",
                    callback_data="storage_security"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Тарифы и продление",
                    callback_data="storage_rates"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="back_to_main"
                )
            ]
        ]
    )


def empty_items_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Заказать звонок",
                    callback_data="request_call"
                )
            ],
        ]
    )


def pickup_delivery_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Самовывоз со склада",
                    callback_data=f"pickup_self_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Доставка на дом",
                    callback_data=f"pickup_delivery_home_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=f"back_to_pickup_{order_id}"
                )
            ]
        ]
    )


def confirm_pickup_kb(order_id: int, pickup_type: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтвердить",
                    callback_data=f"confirm_pickup_{order_id}_{pickup_type}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"cancel_pickup_{order_id}"
                )
            ]
        ]
    )