from aiogram import Router, F, types
from config import MANAGER_TG_ID
from database.repository import get_all_orders, get_all_promo, count_orders_by_promo, set_promo_active
from keyboards.admin import admin_main_kb
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from database.repository import create_promo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in MANAGER_TG_ID


@router.message(F.text == "Админ-панель")
async def admin_panel_button(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔐 Админ-панель:",
        reply_markup=admin_main_kb()
    )




@router.callback_query(F.data == "admin_orders")
async def admin_all_orders(callback: types.CallbackQuery):

    if not is_admin(callback.from_user.id):
        return

    orders = await get_all_orders()

    if not orders:
        await callback.message.answer("Заказов нет.")
        return

    text = "📋 Все заказы:\n\n"

    for order in orders:

        text += (
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
            f"Срок: {order.reserve_until} мес.\n"
            f"Цена: {order.estimated_price} ₽"
            "\n===============================\n"
        )

    await callback.message.answer(text)


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

    await message.answer("Введите процент скидки (например 20):")
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


