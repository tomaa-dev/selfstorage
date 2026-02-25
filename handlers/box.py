import os
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlencode
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardRemove, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    FSInputFile
)
from keyboards.box import (
    generate_delivery_method_kb,
    generate_boxes_kb,
    generate_rental_period_kb,
    generate_confirm_kb,
    generate_request_contact_kb,
    get_promocode_kb,
    generate_payment_kb,
    generate_payment_success_kb
)
from database.repository import (
    create_order, 
    get_or_create_user, 
    get_valid_promo, 
    increase_promo_usage, 
    get_order_by_id,
    update_order,
    send_real_email,
    notify_order_expiring_soon,
    notify_order_expired
)
from keyboards.menu import main_menu_kb
from decouple import config
from config import BOXES, DELIVERY_SETTINGS, DB, PROMO_CODES, WAREHOUSE_ADDRESS
from datetime import datetime, timedelta
import qrcode


router = Router()


class RentBox(StatesGroup):
    selected_box = State()
    rental_period = State()
    fio = State()
    delivery_method = State()
    address = State()
    contact = State() 
    email = State()
    promo = State()
    confirm_order = State()
    payment = State()
    check_payment = State()


def generate_payment_url(order_id: int, amount: int, description: str):
    base_url = "https://paymaster.ru/payment/init"

    params = {
        "merchantId": config('PAYMENT_TOKEN'),
        "amount": str(amount),
        "currency": "RUB",
        "orderId": str(order_id),
        "description": description[:100],
        "testMode": "1",
    }

    return f"{base_url}?{urlencode(params)}"


def generate_qr_code_file(payment_url: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img.save(temp_file.name, 'PNG')
    temp_file.close()
    
    return temp_file.name


@router.message(F.text == "Арендовать бокс")
@router.callback_query(F.data == "pick_box")
async def start_rent_box(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()

    if isinstance(event, types.CallbackQuery):
        message = event.message
        await event.answer()
    else:
        message = event

    await show_boxes(message, state)


async def show_boxes(message: types.Message, state: FSMContext):
    text = "Доступные боксы для аренды:\n\n"

    for box in BOXES:
        text += (
            f"{box['name']}\n"
            f"Размер: {box['size']}\n"
            f"Габариты: {box['dimensions']}\n"
            f"Цена: {box['price_per_month']} ₽/мес\n"
            f"{box['description']}\n\n"
        )

    text += "Выберите подходящий бокс или закажите замеры:"

    await message.answer(
        text, 
        reply_markup=generate_boxes_kb()
    )


@router.callback_query(F.data.startswith("select_box_"))
async def process_select_box(callback: types.CallbackQuery, state: FSMContext):
    box_id = callback.data.replace("select_box_", "")
    box = next((b for b in BOXES if b["id"] == box_id), None)

    if box:
        await state.update_data(selected_box=box)

        await callback.message.answer(
            f"Вы выбрали: {box['name']}\n\n"
            f"Объём: {box['size']}\n"
            f"Габариты: {box['dimensions']}\n"
            f"Стоимость: {box['price_per_month']} ₽/мес\n"
            f"{box['description']}\n\n"
            "Выберите срок аренды:",
            reply_markup=generate_rental_period_kb()
        )

        await state.set_state(RentBox.rental_period)
    await callback.answer()


@router.callback_query(F.data.startswith("period_"))
async def process_rental_period(callback: types.CallbackQuery, state: FSMContext):
    period_map = {
        "period_1": (1, "1 месяц"),
        "period_3": (3, "3 месяца"),
        "period_6": (6, "6 месяцев")
    }

    period_key = callback.data
    months, period_text = period_map.get(period_key, (1, "1 месяц"))
    
    data = await state.get_data()
    box = data.get("selected_box", {})
    
    await state.update_data(rental_months=months, rental_period_text=period_text)
    
    base_price = box.get("price_per_month", 0)
    total_price = base_price * months

    await state.update_data(total_price=total_price)

    await callback.message.answer(
        f"Срок аренды: {period_text}\n"
        f"Итоговая стоимость: {total_price} ₽\n\n"
        "Введите ваше ФИО:"
    )
    
    await state.set_state(RentBox.fio)
    await callback.answer()


@router.message(RentBox.fio)
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    
    await message.answer(
        "Выберите способ доставки вещей:\n\n"
        "ВНИМАНИЕ:\n"
        "При приёме вещей на склад наши специалисты произведут замеры габаритов.\n"
        "Если объём превысит выбранный бокс, мы предложим более подходящий вариант.",
        reply_markup=generate_delivery_method_kb()
    )
    
    await state.set_state(RentBox.delivery_method)


@router.message(RentBox.delivery_method, F.text == "Самовывоз")
async def process_self_delivery(message: types.Message, state: FSMContext):
    await state.update_data(
        delivery_method="Самовывоз",
        address=WAREHOUSE_ADDRESS,
        is_self_delivery=True,
        is_delivery_required=False
    )

    await message.answer(
        f"Адрес склада для самовывоза: {WAREHOUSE_ADDRESS}\n\n"
        "При приёме вещей на склад наши специалисты произведут замеры габаритов ваших вещей.\n\n"
        "Отправьте номер телефона для связи:",
        reply_markup=generate_request_contact_kb()
    )
    await state.set_state(RentBox.contact)


@router.message(RentBox.delivery_method, F.text == "Вывоз вещей - доставка")
async def process_pickup_service(message: types.Message, state: FSMContext):
    await state.update_data(
        delivery_method="Заказать вывоз",
        is_self_delivery=False,
        is_delivery_required=True
    )

    await message.answer(
        "При заборе вещей наш курьер произведёт замеры габаритов!\n\n"
        "Укажите адрес, откуда нужно забрать вещи\n(город, улица, дом, квартира):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RentBox.address)


@router.message(RentBox.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)

    await message.answer(
        "Пожалуйста, отправьте номер телефона (или нажмите «Отправить контакт»):",
        reply_markup=generate_request_contact_kb()
    )
    await state.set_state(RentBox.contact)


@router.message(RentBox.contact)
async def process_contact(message: types.Message, state: FSMContext):
    if message.contact:
        contact = message.contact.phone_number
    else:
        contact = message.text

    await state.update_data(contact=contact)

    await message.answer(
        "Укажите вашу электронную почту для отправки уведомлений:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RentBox.email)


@router.message(RentBox.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)

    await message.answer(
        "Есть промокод? Введите его для получения скидки или напишите 'нет':",
        reply_markup=get_promocode_kb()
    )
    await state.set_state(RentBox.promo)


@router.callback_query(F.data == "skip_promocode")
async def process_skip_promocode(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(promocode=None, discount_percent=0)
    await callback.answer()
    await process_final_summary(callback.message, state)


@router.message(RentBox.promo)
async def process_promo(message: types.Message, state: FSMContext):
    promo_code = message.text.strip()

    if promo_code.lower() == "нет":
        await state.update_data(promo_code=None, discount_percent=0)
        await process_final_summary(message, state)
        return

    promo = await get_valid_promo(promo_code)

    if promo:
        discount_percent = promo.discount_percent
        await increase_promo_usage(promo_code)
        await message.answer(
            f"Поздравляем! Вы получили скидку {discount_percent}%",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.update_data(
            promo_code=promo_code, 
            discount_percent=discount_percent
        )
    else:
        await message.answer(
            "К сожалению, такого промокода не существует или он истёк.\n"
            "Попробуйте ещё раз или нажмите «Пропустить»:",
            reply_markup=get_promocode_kb()
        )
        return

    await process_final_summary(message, state)


async def process_final_summary(message: types.Message, state: FSMContext):
    data = await state.get_data()
    box = data.get("selected_box", {})
    delivery = data.get("delivery_method", "Самовывоз")
    address = data.get("address", "Не указан")
    contact = data.get("contact")
    email = data.get("email")
    fio = data.get("fio")
    need_measurements = data.get("need_measurements", False)
    discount_percent = data.get("discount_percent", 0)
    promo_code = data.get("promo_code")
    is_self_delivery = data.get("is_self_delivery", False)
    is_delivery_required = data.get("is_delivery_required", False)
    rental_months = data.get("rental_months", 1)
    rental_period_text = data.get("rental_period_text", "1 месяц")

    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=30 * rental_months)

    volume_text = f"{box.get('name', '')} ({box.get('size', '')})"
    base_price = box.get("price_per_month", 0)
    total_base = base_price * rental_months

    if is_self_delivery:
        price_after_self_delivery = int(total_base * DELIVERY_SETTINGS["self_delivery_discount"])
        self_delivery_discount = total_base - price_after_self_delivery
    else:
        price_after_self_delivery = total_base
        self_delivery_discount = 0
        
    if discount_percent > 0:
        price = int(price_after_self_delivery * (100 - discount_percent) / 100)
        price_text = (
            f"{price} ₽\n"
            f"(базовая: {base_price} ₽/мес × {rental_months} мес = {total_base} ₽\n"
            f"самовывоз: -{self_delivery_discount} ₽\n"
             f"промокод: -{discount_percent}%)"
            )
    else:
        price = price_after_self_delivery
        if self_delivery_discount > 0:
            price_text = f"{price} ₽ (базовая: {total_base} ₽, самовывоз: -{self_delivery_discount} ₽)"
        else:
            price_text = f"{price} ₽"

    user, created = await get_or_create_user(message.from_user.id)

    order = await create_order(
        user_id=user.id,
        fio=fio,
        volume=volume_text,
        delivery_type=delivery,
        phone=contact,
        estimated_price=price,
        address=address,
        promo_code=promo_code,
        email=email,
        start_date=start_date,
        end_date=end_date,
        is_delivery_required=is_delivery_required
    )

    order_id = order.id

    if is_self_delivery:
        address_text = f"Самовывоз со склада: {WAREHOUSE_ADDRESS}"
        measurement_note = "Замеры будут произведены при приёме вещей на склад"
    else:
        address_text = f"Адрес для вывоза: {address}"
        measurement_note = "Замеры будут произведены курьером при вывозе вещей"

    summary = (
        "Заявка на аренду бокса:\n\n"
        f"Бокс: {volume_text}\n"
        f"Период аренды: {rental_period_text}\n"
        f"Начало хранения: {start_date.strftime('%d.%m.%Y')}\n"
        f"Окончание хранения: {end_date.strftime('%d.%m.%Y')}\n"
        f"Стоимость: {price_text}\n"
        f"Способ доставки: {delivery}\n"
        f"{address_text}\n"
        f"Телефон: {contact}\n"
        f"Почта: {email}\n\n"
        f"{measurement_note}\n"
    )

    if discount_percent > 0 and promo_code:
        summary += f"Промокод: {promo_code} (-{discount_percent}%)\n"

    summary += f"\nНомер заказа: #{order_id}"


    summary += "\n\nДля продолжения нажмите «Оплатить»"

    payment_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплатить",
                    callback_data=f"pay_order_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Перейти на главное меню",
                    callback_data="back_to_main"
                )
            ]
        ]
    )

    await message.answer(summary, reply_markup=payment_kb)

    manager_id = config('ADMIN_CHAT_ID')
    if manager_id:
        try:
            await message.bot.send_message(
                manager_id,
                f"Новая заявка #{order_id}!\n\n{summary}"
            )
        except Exception:
            pass

    await state.update_data(current_order_id=order_id)
    await state.set_state(RentBox.payment)


@router.callback_query(F.data.startswith("pay_order_"))
async def process_pay_order(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("pay_order_", ""))

    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    description = f"Аренда бокса #{order_id}"

    payment_url = generate_payment_url(
        order_id=order_id,
        amount=order.estimated_price,
        description=description
    )

    qr_file_path = generate_qr_code_file(payment_url)
    qr_image = FSInputFile(qr_file_path)

    await callback.message.answer_photo(
        photo=qr_image,
        caption=(
            f"Сканируйте QR-код для оплаты\n\n"
            f"Заказ: #{order_id}\n"
            f"Сумма: {order.estimated_price} ₽\n\n"
            f"Описание: {description}\n"
        ),
        reply_markup=generate_payment_kb(order_id, payment_url)
    )

    try:
        os.unlink(qr_file_path)
    except:
        pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment_"))
async def process_check_payment(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("check_payment_", ""))
    
    order = await get_order_by_id(order_id)
    
    if not order:
        await callback.message.answer("Заказ не найден")
        await callback.answer()
        return

    current_date = datetime.now().date()
    await update_order(order_id, status="PAID", start_date=current_date)

    order = await get_order_by_id(order_id)

    success_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Мои заказы",
                    callback_data="my_orders"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Главное меню",
                    callback_data="back_to_main"
                )
            ]
        ]
    )

    await send_real_email(
        email=order.email,
        subject="Оплата заказа принята - SelfStorage",
        message=f"""Уважаемый {order.fio or 'клиент'}!

Ваш заказ №{order_id} успешно оплачен!

Детали заказа:
Бокс: {order.volume}
Период аренды: с {order.start_date} по {order.end_date}
Сумма: {order.estimated_price} ₽
Способ доставки: {order.delivery_type}

Статус:
{'Доставка запланирована' if order.is_delivery_required else 'Ждем вас на складе'}

Если вы заказали доставку, наш менеджер свяжется с вами в ближайшее время для уточнения деталей.
Спасибо за выбор SelfStorage!
"""
    )

    await callback.message.answer(
        f"Оплата прошла успешно!\n\n"
        f"Заказ: #{order_id}:\n\n"
        f"Сумма: {order.estimated_price} ₽\n"
        f"Дата начала: {current_date.strftime('%d.%m.%Y')}\n"
        f"Дата окончания: {order.end_date.strftime('%d.%m.%Y')}\n\n"
        f"Чек отправлен на вашу почту {order.email}\n\n"
        f"{'Наш менеджер свяжется с вами для уточнения деталей доставки.' if order.is_delivery_required else 'Ждем вас на складе по адресу: ' + WAREHOUSE_ADDRESS}\n\n"
        f"Спасибо за заказ!",
        reply_markup=success_kb
    )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Главное меню\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_boxes")
async def process_back_to_boxes(callback: types.CallbackQuery, state: FSMContext):
    await show_boxes(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "back_to_delivery")
async def process_back_to_delivery(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Выберите способ доставки вещей:",
        reply_markup=generate_delivery_method_kb()
    )
    await state.set_state(RentBox.delivery_method)
    await callback.answer()