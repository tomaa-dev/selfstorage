from database.repository import get_or_create_user, get_user_orders
from aiogram import Router, F, types
from config import ORDER_STATUSES

router = Router()

@router.message(F.text == "Мои заказы")
async def my_orders(message: types.Message):

    user = await get_or_create_user(message.from_user.id)

    orders = await get_user_orders(user.id)

    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "Ваши заказы:\n\n"

    for order in orders:
        status_ru = ORDER_STATUSES.get(order.status, order.status)

        text += (
            f"Заказ №{order.id}\n"
            f"Объём: {order.volume}\n"
            f"Доставка: {order.delivery_type}\n"
            f"Статус: {status_ru}\n"
            f"Цена: {order.estimated_price} ₽\n\n"
        )

    await message.answer(text)