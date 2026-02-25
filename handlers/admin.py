from aiogram import Router, F, types
from config import MANAGER_TG_ID
from database.repository import (
    get_all_orders, 
    get_all_promo, 
    count_orders_by_promo, 
    set_promo_active,
    get_orders_for_delivery,
    get_orders_in_storage,
    get_expired_orders,
    mark_order_delivered,
    mark_order_in_storage,
    update_order,
    get_order_by_id,
    create_promo,
    admin_check_expired_orders,
    get_expired_status_orders,
    get_orders_for_admin_list
)
from keyboards.admin import admin_main_kb 
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from database.repository import create_promo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime


router = Router()


def is_admin(user_id: int):
    return user_id in MANAGER_TG_ID


@router.message(F.text == "Админ-панель")
async def admin_panel_button(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔐 Админ-панель:",
        reply_markup=admin_main_kb()
    )


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.answer(
        "🔐 Админ-панель:",
        reply_markup=admin_main_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_orders")
async def admin_all_orders(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    orders = await get_orders_for_admin_list()

    if not orders:
        await callback.message.answer("Заказов нет.")
        await callback.answer()
        return

    await callback.message.answer("📋 Все заказы:\n")  # заголовок один раз

    for order in orders:
        text = (
            "\n===============================\n"
            f"Заказ №{order.id}\n"
            f"ФИО: {order.fio}\n"
            f"Размер: {order.volume}\n"
            f"Доставка: {order.delivery_type}\n"
            f"Адрес: {order.address}\n"
            f"Телефон: {order.phone}\n"
            f"Промокод: {order.promo_code if order.promo_code else 'нет'}\n"
            f"Начало хранения: {order.start_date}\n"
            f"Окончание хранения: {order.end_date}\n"
            f"Цена: {order.estimated_price} ₽\n"
            "\n===============================\n"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"✅ Принять на склад #{order.id}",
                        callback_data=f"confirm_storage_{order.id}"
                    )
                ]
            ]
        )

        await callback.message.answer(text, reply_markup=keyboard)

    # кнопка "Назад" отдельным сообщением в конце
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back_to_admin")]]
    )
    await callback.message.answer(
        "Назад в меню:",
        reply_markup=back_kb
    )

    await callback.answer()





@router.callback_query(F.data == "admin_delivery")
async def admin_delivery_orders(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    orders = await get_orders_for_delivery()

    if not orders:
        await callback.message.answer(
            "Нет заказов, ожидающих доставки.\n\n"
            "Все заказы либо доставлены, либо не требуют доставки.",
            reply_markup=admin_main_kb()
        )
        await callback.answer()
        return

    text = "Заказы, требующие доставки:\n\n"
    
    for order in orders:
        text += (
            f"Заказ №{order.id}\n"
            f"Клиент: {order.fio or 'Не указано'}\n"
            f"Телефон: {order.phone}\n"
            f"Адрес: {order.address or 'Самовывоз'}\n"
            f"Время: {order.preferred_time or 'Любое'}\n"
            f"Бокс: {order.volume}\n\n"
        )

    text += "Выберите заказ для выполнения доставки:"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for order in orders:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"#{order.id} - {order.fio or 'Клиент'} ({order.phone})",
                callback_data=f"delivery_detail_{order.id}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="Назад в админку", callback_data="back_to_admin")
    ])

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delivery_detail_"))
async def admin_delivery_detail(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.replace("delivery_detail_", ""))
    order = await get_order_by_id(order_id)

    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    # Ссылка на карту
    map_link = f"https://yandex.ru/maps/?text={order.address.replace(' ', '+')}" if order.address else None

    text = (
        f"Доставка заказа №{order.id}\n\n"
        f"Клиент: {order.fio or 'Не указано'}\n"
        f"Телефон: {order.phone}\n\n"
        f"Куда ехать:\n{order.address or 'Клиент заберет самостоятельно'}\n\n"
    )

    if order.preferred_time:
        text += f"⏰ Предпочтительное время: {order.preferred_time}\n"

    text += (
        f"\nДетали заказа:\n"
        f"Бокс: {order.volume}\n"
        f"Сумма к оплате: {order.estimated_price} ₽\n"
        f"Способ оплаты: {order.status}\n"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть карту",
                    url=map_link if map_link else f"https://yandex.ru/maps/?text=Москва"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Доставка выполнена",
                    callback_data=f"mark_delivered_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(text="Назад", callback_data="admin_delivery")
            ]
        ]
    )

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("mark_delivered_"))
async def admin_mark_delivered(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.replace("mark_delivered_", ""))
    order = await get_order_by_id(order_id)

    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    # Отмечаем как доставленный и принятый на склад
    await mark_order_delivered(order_id)
    await mark_order_in_storage(order_id)

    await callback.message.answer(
        f"Заказ №{order_id} отмечен как доставленный!\n\n"
        f"Вещи клиента приняты на склад.\n"
        f"Клиенту отправлено уведомление на почту.",
        reply_markup=admin_main_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_storage")
async def admin_storage_orders(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    processed = await admin_check_expired_orders()   # ✅ ДОБАВИЛИ

    orders = await get_orders_in_storage()
    expired_orders = await get_expired_status_orders()

    text = "Управление складом:\n\n"
    if processed:
        text += f"✅ Обновлено просроченных: {processed}\n\n"

    if orders:
        text += "Активные заказы на складе:\n"
        for order in orders[:10]:  # Показываем первые 10
            if order.end_date:
                days_left = (order.end_date - datetime.date.today()).days
            else:
                days_left = "?"
            text += (
                f"   №{order.id} - {order.fio or 'Клиент'}: "
                f"осталось {days_left} дн.\n"
            )
        if len(orders) > 10:
            text += f"   ... и ещё {len(orders) - 10} заказов\n"

    if expired_orders:
        text += "\nПросроченные заказы:\n"
        for order in expired_orders[:10]:
            days_expired = (datetime.date.today() - order.end_date).days
            text += (
                f"   №{order.id} - {order.fio or 'Клиент'}: "
                f"просрочено на {days_expired} дн.\n"
            )
        if len(expired_orders) > 10:
            text += f"   ... и ещё {len(expired_orders) - 10} заказов\n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Список на складе ({len(orders)})",
                    callback_data="storage_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Просроченные ({len(expired_orders)})",
                    callback_data="expired_list"
                )
            ],
            [
                InlineKeyboardButton(text="Назад", callback_data="back_to_admin")
            ]
        ]
    )

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "storage_list")
async def admin_storage_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    orders = await get_orders_in_storage()

    if not orders:
        await callback.message.answer(
            "На складе нет активных заказов.",
            reply_markup=admin_main_kb()
        )
        await callback.answer()
        return

    text = "Заказы на складе:\n\n"


    for order in orders:
        days_left = (order.end_date - datetime.date.today()).days
        
        text += (
            f"Заказ №{order.id}\n"
            f"Клиент: {order.fio or 'Не указано'}\n"
            f"Телефон: {order.phone}\n"
            f"Почта: {order.email or 'Не указана'}\n"
            f"Бокс: {order.volume}\n"
            f"Окончание: {order.end_date} (через {days_left} дн.)\n\n"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_storage")]
        ]
    )


    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_storage_"))
async def confirm_storage(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.replace("confirm_storage_", ""))

    await mark_order_in_storage(order_id)

    await callback.message.answer(
        f"✅ Заказ №{order_id} подтверждён как принятый на склад.",
        reply_markup=admin_main_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "expired_list")
async def admin_expired_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    orders = await get_expired_status_orders()

    if not orders:
        await callback.message.answer(
            "Нет просроченных заказов!",
            reply_markup=admin_main_kb()
        )
        await callback.answer()
        return

    text = "Просроченные заказы:\n\n"

    for order in orders:
        if order.end_date:
            days_expired = (datetime.date.today() - order.end_date).days
            end_text = f"{order.end_date} ({days_expired} дн. назад)"
        else:
            end_text = "не указано"
        
        text += (
            f"Заказ №{order.id}\n"
            f"Клиент: {order.fio or 'Не указано'}\n"
            f"Телефон: {order.phone}\n"
            f"Почта: {order.email or 'Не указана'}\n"
            f"Бокс: {order.volume}\n"
            f"Истёк: {order.end_date} ({days_expired} дн. назад)\n\n"
        )

    text += "Рекомендуется связаться с клиентами для продления или вывоза вещей."

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_storage")]
        ]
    )

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


class AddPromo(StatesGroup):
    code = State()
    discount = State()
    active_from = State()
    active_to = State()


@router.callback_query(F.data == "add_promo")
async def add_promo_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.answer("Введите название промокода:")
    await state.set_state(AddPromo.code)
    await callback.answer()


@router.message(AddPromo.code)
async def add_promo_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)

    await message.answer("Введите процент скидки:")
    await state.set_state(AddPromo.discount)


@router.message(AddPromo.discount)
async def add_promo_discount(message: types.Message, state: FSMContext):

    await state.update_data(discount=int(message.text))

    await message.answer("Введите дату начала (гггг-мм-дд) или напишите 'нет':")
    await state.set_state(AddPromo.active_from)


@router.message(AddPromo.active_from)
async def add_promo_active_from(message: types.Message, state: FSMContext):

    if message.text.lower() != "нет":
        await state.update_data(active_from=message.text)
    else:
        await state.update_data(active_from=None)

    await message.answer("Введите дату окончания (гггг-мм-дд) или напишите 'нет':")
    await state.set_state(AddPromo.active_to)


@router.message(AddPromo.active_to)
async def add_promo_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    if data.get("active_from"):
        active_from = datetime.datetime.strptime(
            data.get("active_from"), "%Y-%m-%d"
        ).date()
    else:
        active_from = None

    if message.text.lower() != "нет":
        active_to = datetime.datetime.strptime(
            message.text, "%Y-%m-%d"
        ).date()
    else:
        active_to = None

    await create_promo(
        code=data.get("code"),
        discount_percent=data.get("discount"),
        active_from=active_from,
        active_to=active_to
    )

    await message.answer(f"Промокод {data.get('code')} добавлен со скидкой {data.get('discount')}%")

    await state.clear()


@router.callback_query(F.data == "promo_stats")
async def promo_stats(callback: types.CallbackQuery):

    if not is_admin(callback.from_user.id):
        return

    promos = await get_all_promo()

    text = "Список промокодов:\n"

    if not promos:
        await callback.message.answer("Промокодов нет.")
        return

    for promo in promos:
        count = await count_orders_by_promo(promo.code)
        text += f"{promo.code} — использован {count} раз\n"

        status = "🟢 Активен" if promo.is_active else "🔴 Неактивен"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Выключить" if promo.is_active else "Включить",
                        callback_data=f"toggle_promo_{promo.code}"
                    )
                ]
            ]
        )

        await callback.message.answer(
            f"Промокод: {promo.code}\n"
            f"Скидка: {promo.discount_percent}%\n"
            f"Дата начала: {promo.active_from}\n"
            f"Дата окончания: {promo.active_to}\n"
            f"Статус: {status}",
            reply_markup=keyboard
        )

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_promo_"))
async def toggle_promo(callback: types.CallbackQuery):

    if not is_admin(callback.from_user.id):
        return

    code = callback.data.replace("toggle_promo_", "")

    promos = await get_all_promo()

    for promo in promos:
        if promo.code == code:
            new_status = not promo.is_active
            await set_promo_active(code, new_status)

            status_text = "включен" if new_status else "выключен"

            await callback.message.answer(
                f"Промокод {code} теперь {status_text}."
            )
            break

    await callback.answer()