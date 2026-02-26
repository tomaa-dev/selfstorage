from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.repository import (
    get_or_create_user, 
    get_user_orders, 
    get_order_by_id,
    update_order,
    send_real_email
)
from keyboards.menu import main_menu_kb
from keyboards.things import (
    items_list_kb, 
    extend_period_kb, 
    confirm_extend_kb,
    item_details_kb,
    storage_info_kb,
    empty_items_kb,
    pickup_delivery_kb,
    confirm_pickup_kb
)
from datetime import datetime, timedelta
from config import BOXES, WAREHOUSE_ADDRESS, DELIVERY_SETTINGS, MANAGER_TG_ID
import qrcode
import tempfile
import os


router = Router()


class ExtendOrder(StatesGroup):
    select_period = State()
    confirm = State()


def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img.save(temp_file.name, 'PNG')
    temp_file.close()
    
    return temp_file.name


@router.message(F.text == "Список вещей")
async def my_items(message: types.Message):
    user, _ = await get_or_create_user(message.from_user.id)
    
    orders = await get_user_orders(user.id)
    
    active_orders = [
        order for order in orders 
        if order.status in ["PAID", "IN_STORAGE"]
    ]
    
    if not active_orders:
        await message.answer(
            "Список вещей на хранении\n\n"
            "У вас пока нет вещей на хранении.\n"
            "Арендуйте бокс, чтобы начать хранить вещи!",
            reply_markup=empty_items_kb()
        )
        return
    
    text = "Ваши вещи на хранении\n\n"
    
    for i, order in enumerate(active_orders, 1):
        if order.volume:
            if "замеры" in order.volume.lower():
                content_type = "Требуются замеры"
            else:
                content_type = f"Бокс: {order.volume}"
        else:
            content_type = "Вещи на хранении"

        start_date = order.start_date.strftime("%d.%m.%Y") if order.start_date else "не указана"
        end_date = order.end_date.strftime("%d.%m.%Y") if order.end_date else "не указана"

        days_left = ""
        if order.end_date:
            today = datetime.now().date()
            days = (order.end_date - today).days
            if days > 0:
                days_left = f"\nОсталось дней: {days}"
            elif days == 0:
                days_left = "\nИстекает сегодня!"
            else:
                days_left = "\nСрок истёк"

        delivery_info = ""
        if order.is_delivery_required:
            delivery_info = "\nЗаказана доставка"
        elif order.delivery_type and "самовывоз" in order.delivery_type.lower():
            delivery_info = "\nСамовывоз со склада"

        promo_info = ""
        if order.promo_code:
            promo_info = f"\nПромокод: {order.promo_code}"
        
        text += (
            f"Заказ #{order.id}\n"
            f"{content_type}\n"
            f"Период: {start_date} - {end_date}\n"
            f"Стоимость: {order.estimated_price} ₽"
            f"{days_left}"
            f"{delivery_info}"
            f"{promo_info}\n\n"
        )


    await message.answer(
        text,
        reply_markup=items_list_kb(active_orders[-1].id)
    )

@router.callback_query(F.data.startswith("pickup_full_"))
async def pickup_full(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("pickup_full_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    
    await callback.message.answer(
        f"Забор вещей со склада\n\n"
        f"Заказ #{order.id}\n"
        f"Бокс: {order.volume}\n\n"
        "Выберите способ получения вещей:",
        reply_markup=pickup_delivery_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pickup_partial_"))
async def pickup_partial(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("pickup_partial_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    
    await callback.message.answer(
        f"Частичный забор вещей\n\n"
        f"Заказ #{order.id}\n"
        f"Бокс: {order.volume}\n\n"
        "Вы можете забрать часть вещей, остальные будут храниться до конца срока аренды.\n\n"
        "Выберите способ получения:",
        reply_markup=pickup_delivery_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pickup_delivery_"))
async def pickup_delivery(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("pickup_delivery_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    base_delivery = DELIVERY_SETTINGS.get('pickup_service_base', 500)
    price_per_km = DELIVERY_SETTINGS.get('pickup_per_km', 15)
    
    await callback.message.answer(
        f"Доставка вещей на дом\n\n"
        f"Заказ #{order.id}\n"
        f"Бокс: {order.volume}\n\n"
        f"Адрес доставки: {order.address}\n\n"
        f"Стоимость доставки:\n"
        f"База: {base_delivery} ₽ + {price_per_km} ₽/км\n\n"
        f"Точную стоимость вам сообщит менеджер при подтверждении.\n\n"
        "Менеджер свяжется с вами для уточнения деталей и подтверждения заказа.",
        reply_markup=confirm_pickup_kb(order_id, "delivery")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pickup_self_"))
async def pickup_self(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("pickup_self_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    qr_data = f"SELFSTORAGE_PICKUP:{order_id}:{order.fio or 'CLIENT'}"
    qr_path = generate_qr_code(qr_data)
    
    await callback.message.answer_photo(
        photo=types.FSInputFile(qr_path),
        caption=(
            f"Самовывоз со склада\n\n"
            f"Заказ #{order.id}\n"
            f"Бокс: {order.volume}\n\n"
            f"Адрес склада:\n{WAREHOUSE_ADDRESS}\n\n"
            f"Предъявите QR-код сотруднику склада для получения вещей.\n\n"
            f"Время работы: Ежедневно с 9:00 до 21:00"
        )
    )

    if order.email:
        await send_real_email(
            email=order.email,
            subject=f"QR-код для получения вещей - Заказ #{order.id}",
            message=f"""Уважаемый {order.fio or 'клиент'}!
			Вы забрали вещи со склада!
			Детали заказа:
			Заказ №{order.id}
			Бокс: {order.volume}
			Адрес склада: {WAREHOUSE_ADDRESS}
			QR-код для получения вещей был отправлен в этом чате.
			С уважением,
			Команда SelfStorage"""
        )
    
    try:
        os.unlink(qr_path)
    except:
        pass
    
    await callback.message.answer(
        "Вы можете забрать вещи со склада.\n\n"
        "Если у вас остались вещи на хранении, они будут храниться до конца срока аренды.",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pickup_delivery_home_"))
async def pickup_delivery_home(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("pickup_delivery_home_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    

    qr_data = f"SELFSTORAGE_PICKUP:{order_id}:{order.fio or 'CLIENT'}"
    qr_path = generate_qr_code(qr_data)

    await callback.message.answer_photo(
        photo=types.FSInputFile(qr_path),
        caption=(
            f"Доставка вещей\n\n"
            f"Заказ #{order.id}\n"
            f"Бокс: {order.volume}\n\n"
            f"Адрес доставки: {order.address}\n\n"
            f"QR-код- для идентификации заказа при получении.\n\n"
            f"Менеджер свяжется с вами для подтверждения времени доставки."
        )
    )
    
    try:
        os.unlink(qr_path)
    except:
        pass

    from config import MANAGER_TG_ID
    for manager_id in MANAGER_TG_ID:
        try:
            await callback.message.bot.send_message(
                manager_id,
                f"Запрос доставки\n\n"
                f"Заказ #{order.id}\n"
                f"Клиент: {order.fio or 'Не указано'}\n"
                f"Телефон: {order.phone}\n"
                f"Адрес: {order.address}\n"
                f"Бокс: {order.volume}\n"
                f"Тип: Доставка на дом"
            )
        except Exception:
            pass

    if order.email:
        await send_real_email(
            email=order.email,
            subject=f"Доставка вещей - Заказ #{order.id}",
            message=f"""Уважаемый {order.fio or 'клиент'}!
                Вы запросили доставку вещей на дом!
                Детали заказа: Заказ №{order.id} Бокс: {order.volume} Адрес доставки: {order.address}
                Менеджер свяжется с вами в ближайшее время для подтверждения времени доставки.
                С уважением, Команда SelfStorage""" 
        )

        await callback.message.answer(
            "Запрос на доставку оформлен!\n\n"
            "Менеджер свяжется с вами для подтверждения времени доставки.\n\n"
            "Если у вас остались вещи на хранении, они будут храниться до конца срока аренды.",
            reply_markup=main_menu_kb(callback.from_user.id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_pickup_"))
async def confirm_pickup(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    order_id = int(parts[2])
    pickup_type = parts[3]
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("❌ Заказ не найден")
        await callback.answer()
        return

    qr_data = f"SELFSTORAGE_PICKUP:{order_id}:{order.fio or 'CLIENT'}"
    qr_path = generate_qr_code(qr_data)
    
    if pickup_type == "self":
        address_text = WAREHOUSE_ADDRESS
        action_text = "самовывоз"
    else:
        address_text = order.address
        action_text = "доставка"
    
    await callback.message.answer_photo(
        photo=types.FSInputFile(qr_path),
        caption=(
            f"Подтверждение забора вещей\n\n"
            f"Заказ #{order.id}\n"
            f"Бокс: {order.volume}\n\n"
            f"Адрес: {address_text}\n\n"
            f"Предъявите QR-код для получения вещей.\n\n"
            f"Время работы склада: Ежедневно 9:00-21:00"
        )
    )
    
    try:
        os.unlink(qr_path)
    except:
        pass

    await update_order(order_id, status="COMPLETED")
    
    await callback.message.answer(
        f"Забор вещей подтверждён!\n\n"
        f"Тип: {action_text}\n"
        f"Заказ №{order.id}\n\n"
        "Спасибо, что использовали SelfStorage!",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_pickup_"))
async def cancel_pickup(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("cancel_pickup_", ""))
    
    await callback.message.answer(
        "Забор вещей отменён",
        reply_markup=items_list_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_order_"))
async def extend_order(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("extend_order_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    
    await callback.message.answer(
        f"Продление аренды\n\n"
        f"Заказ #{order.id}\n"
        f"Текущая стоимость: {order.estimated_price} ₽/мес\n\n"
        "Выберите период продления:",
        reply_markup=extend_period_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_1_"))
async def extend_1_month(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    await extend_by_months(callback, order_id, 1)


@router.callback_query(F.data.startswith("extend_3_"))
async def extend_3_months(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    await extend_by_months(callback, order_id, 3)


@router.callback_query(F.data.startswith("extend_6_"))
async def extend_6_months(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    await extend_by_months(callback, order_id, 6)


async def extend_by_months(callback: types.CallbackQuery, order_id: int, months: int):
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    new_end_date = order.end_date + timedelta(days=30 * months) if order.end_date else datetime.now().date() + timedelta(days=30 * months)

    price_per_month = order.estimated_price
    additional_price = price_per_month * months
    
    await callback.message.answer(
        f"Подтверждение продления\n\n"
        f"Заказ #{order.id}\n"
        f"Текущая дата окончания: {order.end_date.strftime('%d.%m.%Y') if order.end_date else 'не установлена'}\n"
        f"Новая дата окончания: {new_end_date.strftime('%d.%m.%Y')}\n"
        f"Период продления: {months} месяц(ев)\n"
        f"Доплата: {additional_price} ₽\n\n"
        f"После продления вы сможете оплатить дополнительную сумму.",
        reply_markup=confirm_extend_kb(order_id, months, additional_price)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_extend_"))
async def confirm_extend(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    order_id = int(parts[2])
    months = int(parts[3])
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    new_end_date = order.end_date + timedelta(days=30 * months) if order.end_date else datetime.now().date() + timedelta(days=30 * months)
    additional_price = order.estimated_price * months
    new_total_price = order.estimated_price + additional_price

    await update_order(
        order_id,
        end_date=new_end_date,
        estimated_price=new_total_price
    )
    
    await callback.message.answer(
        f"Аренда продлена!\n\n"
        f"Заказ #{order.id}\n"
        f"Новая дата окончания: {new_end_date.strftime('%d.%m.%Y')}\n"
        f"Доплата: {additional_price} ₽\n\n"
        f"Менеджер свяжется с вами для подтверждения оплаты.",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_extend_"))
async def cancel_extend(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("cancel_extend_", ""))
    
    await callback.message.answer(
        "Продление отменено",
        reply_markup=items_list_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item_desc_"))
async def item_description(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("item_desc_", ""))
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    
    await callback.message.answer(
        f"Описание содержимого\n\n"
        f"Заказ #{order.id}\n"
        f"Объём: {order.volume}\n"
        f"Адрес: {order.address or 'не указан'}",
        reply_markup=item_details_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item_size_"))
async def item_size(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("item_size_", ""))
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    box_info = ""
    for box in BOXES:
        if box["name"] in order.volume:
            box_info = (
                f"{box['name']}\n"
                f"Размер: {box['size']}\n"
                f"Габариты: {box['dimensions']}\n"
                f"Цена: {box['price_per_month']} ₽/мес"
            )
            break
    
    if not box_info:
        box_info = "Информация о боксе недоступна"
    
    await callback.message.answer(
        f"Размер бокса\n\n"
        f"Заказ #{order.id}\n\n"
        f"{box_info}",
        reply_markup=item_details_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item_dates_"))
async def item_dates(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("item_dates_", ""))
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    
    start_date = order.start_date.strftime("%d.%m.%Y") if order.start_date else "не установлена"
    end_date = order.end_date.strftime("%d.%m.%Y") if order.end_date else "не установлена"
    
    days_left = "∞"
    if order.end_date:
        days = (order.end_date - datetime.now().date()).days
        days_left = str(days) if days > 0 else "0"
    
    await callback.message.answer(
        f"Даты хранения\n\n"
        f"Заказ #{order.id}\n"
        f"Начало: {start_date}\n"
        f"Окончание: {end_date}\n"
        f"Осталось дней: {days_left}",
        reply_markup=item_details_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item_payments_"))
async def item_payments(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("item_payments_", ""))
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return
    
    status_text = {
        "CREATED": "Ожидает оплаты",
        "PAID": "Оплачен",
        "IN_STORAGE": "На хранении",
        "COMPLETED": "Завершён",
        "CANCELLED": "Отменён",
        "EXPIRED": "Истёк"
    }.get(order.status, "Неизвестно")
    
    await callback.message.answer(
        f"История оплат\n\n"
        f"Заказ #{order.id}\n"
        f"Статус: {status_text}\n"
        f"Сумма: {order.estimated_price} ₽\n"
        f"Промокод: {order.promo_code or 'нет'}",
        reply_markup=item_details_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_items_"))
async def back_to_items(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("back_to_items_", ""))
    await callback.message.answer(
        "Вернуться к заказу",
        reply_markup=items_list_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_items_list")
async def back_to_items_list(callback: types.CallbackQuery):
    await my_items(callback.message)
    await callback.answer()


@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: types.CallbackQuery):
    await callback.message.answer(
        "Связаться с менеджером\n\n"
        "Телефон: +7-918-714-58-30\n"
        "Telegram: @selfstorage_bot\n\n"
        "Мы работаем ежедневно с 9:00 до 21:00"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.answer(
        "Главное меню\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data == "storage_prepare")
async def storage_prepare(callback: types.CallbackQuery):
    await callback.message.answer(
        "Как подготовить вещи к хранению\n\n"
        "1. Упакуйте вещи в коробки или мешки\n"
        "2. Очистите вещи от грязи и пыли\n"
        "3. Используйте пломбы или замки\n"
        "4. Составьте опись вещей\n\n",
        reply_markup=storage_info_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "storage_delivery")
async def storage_delivery(callback: types.CallbackQuery):
    from config import WAREHOUSE_ADDRESS, DELIVERY_SETTINGS
    
    await callback.message.answer(
        f"Доставка и самовывоз\n\n"
        "Самовывоз:\n"
        f"Адрес склада: {WAREHOUSE_ADDRESS}\n"
        "Скидка за самовывоз: 20%\n\n"
        "Доставка:\n"
        f"Базовая стоимость: {DELIVERY_SETTINGS.get('pickup_service_base', 500)} ₽\n"
        f"За 1 км: {DELIVERY_SETTINGS.get('pickup_per_km', 15)} ₽",
        reply_markup=storage_info_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "storage_security")
async def storage_security(callback: types.CallbackQuery):
    await callback.message.answer(
        "Безопасность хранения\n\n"
        "Охрана 24/7\n"
        "Видеонаблюдение\n"
        "Пожарная сигнализация\n"
        "Контроль доступа\n"
        "Страхование\n\n"
        "Наши склады оборудованы современными системами безопасности.\n"
        "Каждый бокс оснащён индивидуальным замком.\n"
        "Доступ к складу только у авторизованных лиц.",
        reply_markup=storage_info_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "storage_rates")
async def storage_rates(callback: types.CallbackQuery):
    from config import BOXES, DELIVERY_SETTINGS
    
    text = "Тарифы и продление\n\n"
    
    for box in BOXES:
        text += (
            f"{box['name']}\n"
            f"Размер: {box['size']}\n"
            f"Цена: {box['price_per_month']} ₽/мес\n"
            f"{box['description']}\n\n"
        )
    
    text += (
        "Самовывоз: скидка 20%\n"
        f"Доставка: {DELIVERY_SETTINGS.get('pickup_service_base', 500)} ₽ "
        f"+ {DELIVERY_SETTINGS.get('pickup_per_km', 15)} ₽/км\n\n"
        "Промокоды:\n"
        "Применяйте промокоды при оформлении заказа для получения скидки."
    )
    
    await callback.message.answer(
        text,
        reply_markup=storage_info_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "request_call")
async def request_call(callback: types.CallbackQuery):
    from config import MANAGER_TG_ID
    
    await callback.message.answer(
        "Заказать звонок\n\n"
        "Оставьте ваш номер телефона, и наш менеджер свяжется с вами в ближайшее время.\n\n"
        "Или позвоните нам самостоятельно:\n"
        "Телефон: +7-918-714-58-30\n\n"
        "Мы работаем ежедневно с 9:00 до 21:00"
    )
    await callback.answer()


@router.callback_query(F.data == "pick_box")
async def pick_box(callback: types.CallbackQuery):
    from handlers.box import show_boxes
    
    await show_boxes(callback.message, callback.message.bot.get('state', None))
    await callback.answer()