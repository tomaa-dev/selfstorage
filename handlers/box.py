import uuid
import os
import tempfile
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
    generate_delivery_method_for_measurements_kb,
    generate_boxes_kb,
    generate_confirm_kb,
    generate_request_contact_kb,
    get_promocode_kb,
    generate_payment_kb,
    generate_payment_success_kb
)
from database.repository import create_order, get_or_create_user, get_valid_promo, increase_promo_usage, get_order_by_id
from keyboards.menu import main_menu_kb
from decouple import config
from config import BOXES, DELIVERY_SETTINGS, DB, PROMO_CODES, WAREHOUSE_ADDRESS
from datetime import datetime
import qrcode
from io import BytesIO


router = Router()


class RentBox(StatesGroup):
    delivery_method = State()
    address = State()
    volume = State()
    contact = State() 
    email = State()
    promo = State()
    selected_box = State()
    fio = State()
    payment = State()
    check_payment = State()


@router.message(F.text == "Арендовать бокс")
@router.callback_query(F.data == "pick_box")
async def start_rent_box(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()

    if isinstance(event, types.CallbackQuery):
        message = event.message
        await event.answer()
    else:
        message = event


def generate_payment_url(order_id: int, amount: int, description: str) -> str:
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


def urlencode(params: dict):
    return "&".join([f"{k}={v}" for k, v in params.items()])


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
            "Выберите способ доставки вещей:",
            reply_markup=generate_delivery_method_kb()
        )

        await state.set_state(RentBox.delivery_method)
    await callback.answer()


@router.callback_query(F.data == "need_measurements")
async def process_need_measurements(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите ваше ФИО:"
    )

    await state.set_state(RentBox.fio)
    await callback.answer()


@router.message(RentBox.fio)
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)

    await message.answer(
        "📱 Пожалуйста, оставьте ваш контактный номер телефона для связи:\n"
        "(Например: +7 918 123-45-67)"
    )

        "Замеры будут произведены при вывозе ваших вещей\n\n"
        "Специалист приедет к вам, оценит объём и поможет подобрать оптимальный размер бокса.",
        reply_markup=generate_delivery_method_for_measurements_kb()
    )

    await state.update_data(selected_box=None, need_measurements=True)
    await state.set_state(RentBox.delivery_method)
    await callback.answer()


@router.message(RentBox.delivery_method, F.text == "Привезу сам")
async def process_self_delivery(message: types.Message, state: FSMContext):
    await state.update_data(
        delivery_method=message.text,
        address=WAREHOUSE_ADDRESS,
        is_self_delivery=True
    )

    await message.answer(
        f"Адрес склада для самовывоза:{WAREHOUSE_ADDRESS}\n\n"
        f"Пожалуйста, отправьте номер телефона для связи:",
        reply_markup=generate_request_contact_kb()
    )
    await state.set_state(RentBox.contact)


@router.message(RentBox.delivery_method, F.text == "Заказать самовывоз")
async def process_pickup_service(message: types.Message, state: FSMContext):
    await state.update_data(
        delivery_method=message.text,
        is_self_delivery=False
    )

    await message.answer(
        "Укажите адрес, откуда нужно забрать вещи (город, улица, дом, квартира):",
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
    await state.update_data(contact=message.text)

    await message.answer("Введите промокод (если есть) или напишите 'нет':")

    await state.set_state(RentBox.promo)

@router.message(RentBox.promo)
async def process_promo(message: types.Message, state: FSMContext):
    promo_code = message.text.strip()

    data = await state.get_data()
    fio = data.get("fio")
    box = data.get("selected_box", {})
    delivery = data.get("delivery_method", "Привезу сам")
    address = data.get("address", "Не указан")
    volume = data.get("volume", "Не указан")
    contact = data.get("contact")

    price = box.get("price_per_month", 0)

    if delivery == "Привезу сам":
        price = int(price * DELIVERY_SETTINGS["self_delivery_discount"])

    applied_code = None

    if promo_code.lower() != "нет":
        promo = await get_valid_promo(promo_code)

        if promo:
            price = int(price * (1 - promo.discount_percent / 100))
            await increase_promo_usage(promo_code)
            applied_code = promo_code
            await message.answer("Промокод применён!")
        else:
            await message.answer("Промокод недействителен.")

    summary = (
        "Заявка на аренду бокса:\n\n"
        f"Бокс: {box.get('name', 'Не выбран')} ({box.get('size', '')})\n"
        f"Стоимость: {price} ₽/мес\n"
        f"Способ доставки: {delivery}\n"
        f"Адрес: {address}\n"
        f"Размер: {volume}\n"
        f"Телефон: {contact}\n"
        f"Промокод: {applied_code if applied_code else 'нет'}\n\n"
        "Ваша заявка отправлена! Наш менеджер свяжется с вами в ближайшее время."
    )

    await message.answer(summary)
    # Получаем пользователяз
    user, created = await get_or_create_user(message.from_user.id)
    # Создаём заказ в БД
    await create_order(
        user_id=user.id,
        fio=fio,
        volume=volume,
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
        "Есть промокод? Введите его для получения скидки:",
        reply_markup=get_promocode_kb()
    )
    await state.set_state(RentBox.promocode)


@router.callback_query(F.data == "skip_promocode")
async def process_skip_promocode(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(promocode=None, discount_percent=0)
    await callback.answer()
    await process_final_summary(callback.message, state)


@router.message(RentBox.promocode)
async def process_promocode(message: types.Message, state: FSMContext):
    users_promocode = message.text.strip().lower()

    promo_found = None
    for promo in PROMO_CODES:
        if promo["code"].lower() == users_promocode and promo.get("is_active", True):
            promo_found = promo
            break
    
    if promo_found:
        today = datetime.now().strftime("%Y-%m-%d")
        active_from = promo_found.get("active_from", "")
        active_to = promo_found.get("active_to", "")
        
        is_valid = True
        if active_from and today < active_from:
            is_valid = False
        if active_to and today > active_to:
            is_valid = False

        if is_valid:
            discount_percent = promo_found["discount_percent"]
            await message.answer(
                f"Поздравляем! Вы получили скидку {discount_percent}%",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.update_data(
                promocode=users_promocode, 
                discount_percent=discount_percent
            )
        else:
            await message.answer(
                "К сожалению, срок действия этого промокода истёк.",
                reply_markup=get_promocode_kb()
            )
            return
    else:
        await message.answer(
            "К сожалению, такого промокода не существует.\n"
            "Попробуйте ещё раз или нажмите «Пропустить»:",
            reply_markup=get_promocode_kb()
        )
        return
    await process_final_summary(message, state)


async def process_final_summary(message: types.Message, state: FSMContext):
    data = await state.get_data()
    box = data.get("selected_box") or {}
    delivery = data.get("delivery_method", "Привезу сам")
    address = data.get("address", "Не указан")
    contact = data.get("contact", "Не указан")
    email = data.get("email")
    need_measurements = data.get("need_measurements", False)
    discount_percent = data.get("discount_percent", 0)
    promocode = data.get("promocode")
    is_self_delivery = data.get("is_self_delivery", False)


    if need_measurements:
        volume_text = "Требуются замеры"
        price = 0
        price_text = "Будет определена после замеров"
    else:
        volume_text = f"{box.get('name', '')} ({box.get('size', '')})"
        base_price = box.get("price_per_month", 0)

        if is_self_delivery:
            price_after_self_delivery = int(base_price * DELIVERY_SETTINGS["self_delivery_discount"])
            self_delivery_discount = base_price - price_after_self_delivery
        else:
            price_after_self_delivery = base_price
            self_delivery_discount = 0

        
        if discount_percent > 0:
            price = int(price_after_self_delivery * (100 - discount_percent) / 100)
            price_text = (
                f"{price} ₽\n"
                f"(базовая: {base_price} ₽/мес, "
                f"самовывоз: -{self_delivery_discount} ₽, "
                f"промокод: -{discount_percent}%)"
            )
        else:
            price = price_after_self_delivery
            if self_delivery_discount > 0:
                price_text = (
                    f"{price} ₽\n"
                    f"(базовая: {base_price} ₽/мес, самовывоз: -{self_delivery_discount} ₽)"
                )
            else:
                price_text = f"{price} ₽/мес"

    user = await get_or_create_user(message.from_user.id)

    order = await create_order(
        user_id=user.id,
        volume=volume_text,
        delivery_type=delivery,
        phone=contact,
        estimated_price=price,
        address=address,
        promo_code=applied_code
    )

    order_id = order.id

    if is_self_delivery:
        address_text = f"Адрес склада: {address}"
    else:
        address_text = f"Адрес для вывоза: {address}"

    summary = (
        "Заявка на аренду бокса:\n\n"
        f"Бокс: {volume_text}\n"
        f"Стоимость: {price_text}\n"
        f"Способ доставки: {delivery}\n"
        f"{address_text}\n"
        f"Телефон: {contact}\n"
        f"Почта: {email}\n"
    )

    if discount_percent > 0 and promocode:
        summary += f"Промокод: {promocode} (-{discount_percent}%)\n"

    summary += f"\nНомер заказа: #{order_id}"

    if not need_measurements:
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
                        text="Оплатить позже",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
        
        await message.answer(summary, reply_markup=payment_kb)
    else:
        summary += "\n\nВаша заявка отправлена! Наш менеджер свяжется с вами в ближайшее время."
        await message.answer(summary, reply_markup=ReplyKeyboardRemove())

    manager_id = config('ADMIN_CHAT_ID')
    if manager_id:
        try:
            await message.bot.send_message(
                manager_id,
                f"Новая заявка #{order_id}!\n\n{summary}"
            )
        except Exception:
            pass

    await state.clear()


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

    await callback.message.answer(
        f"Оплата прошла успешно!\n\n"
        f"Заказ: #{order_id}:\n\n"
        f"Сумма: {order.estimated_price} ₽\n"
        f"Статус оплаты: ОПЛАЧЕН\n\n"
        f"Наш менеджер свяжется с вами в ближайшее время для уточнения деталей доставки.\n"
        f"Спасибо за заказ!",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Главное меню\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb()
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