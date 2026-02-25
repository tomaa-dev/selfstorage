from database.repository import get_or_create_user, get_user_orders
from aiogram import Router, F, types


router = Router()


@router.message(F.text == "Мои заказы")
@router.callback_query(F.data == "my_orders")
async def my_orders(event: types.Message | types.CallbackQuery):
    STATUS_TRANSLATIONS = {
        "CREATED": "Создано",
        "PAID": "Оплачен",
        "CANCELLED": "Отменён"
    }


    if isinstance(event, types.CallbackQuery):
        message = event.message
        tg_id = event.from_user.id
        await event.answer()
    else:
        message = event
        tg_id = event.from_user.id

    user, _ = await get_or_create_user(tg_id)
    orders = await get_user_orders(user.id)


    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "Ваши заказы:\n\n"
    for order in orders:
        status_text = STATUS_TRANSLATIONS.get(order.status, order.status)
        text += (
            f"Заказ №{order.id}\n"
            f"ФИО: {order.fio or 'Не указано'}\n"
            f"Объём: {order.volume}\n"
            f"Доставка: {order.delivery_type}\n"
            f"Цена: {order.estimated_price} ₽\n"
            
            f"Статус: {status_text}\n\n"
        )
    await message.answer(text)