from database.repository import get_or_create_user, get_user_orders
from aiogram import Router, F, types


router = Router()


@router.message(F.text == "Мои заказы")
async def my_orders(message: types.Message):

    user, created = await get_or_create_user(message.from_user.id)

    orders = await get_user_orders(user.id)

    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "Ваши заказы:\n\n"

    for order in orders:

        text += (
            f"Заказ №{order.id}\n"
            f"ФИО: {order.fio}\n"
            f"Размер: {order.volume}\n"
            f"Заказ №{order.id}\n"
            f"Объём: {order.volume}\n"
            f"Доставка: {order.delivery_type}\n"
            f"Цена: {order.estimated_price} ₽\n\n"
        )

    await message.answer(text)