from aiogram import Router, F, types
from config import MANAGER_TG_ID
from database.repository import get_all_orders, get_all_promo, count_orders_by_promo
from keyboards.admin import admin_main_kb
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


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

from database.repository import create_promo

@router.message(AddPromo.discount)
async def add_promo_discount(message: types.Message, state: FSMContext):

    data = await state.get_data()
    code = data.get("code")

    discount = int(message.text)

    await create_promo(code=code, discount_percent=discount)

    await message.answer(f"Промокод {code} добавлен со скидкой {discount}%")

    await state.clear()

@router.callback_query(F.data == "promo_stats")
async def promo_stats(callback: types.CallbackQuery):

    if not is_admin(callback.from_user.id):
        return

    promos = await get_all_promo()

    text = "Список промокодов:\n"

    for promo in promos:
        count = await count_orders_by_promo(promo.code)
        text += f"{promo.code} — использован {count} раз\n"

    await callback.message.answer(text)
    await callback.answer()

