from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from keyboards.box import (
    generate_delivery_method_kb,
    generate_volume_kb,
    generate_boxes_kb,
    generate_confirm_kb
)
from config import BOXES, DELIVERY_SETTINGS, DB
from database.repository import create_order, get_or_create_user


router = Router()


class RentBox(StatesGroup):
    delivery_method = State()
    address = State()
    volume = State()
    contact = State()
    selected_box = State()


@router.message(F.text == "Арендовать бокс")
@router.callback_query(F.data == "pick_box")
async def start_rent_box(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()

    if isinstance(event, types.CallbackQuery):
        message = event.message
        await event.answer()
    else:
        message = event
    
    await message.answer(
        "Выберите способ доставки вещей:",
        reply_markup=generate_delivery_method_kb()
    )
    await state.set_state(RentBox.delivery_method)


@router.message(RentBox.delivery_method, F.text.in_(["Привезу сам", "Закажите вывоз"]))
async def process_delivery_method(message: types.Message, state: FSMContext):
    await state.update_data(delivery_method=message.text)
    await message.answer(
        "Укажите адрес (город, улица, дом):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RentBox.address)


@router.message(RentBox.address)
async def process_address_text(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await ask_volume(message, state)


async def ask_volume(message: types.Message, state: FSMContext):
    await message.answer(
        "Укажите объём вещей или опишите их:",
        reply_markup=generate_volume_kb()
    )
    await state.set_state(RentBox.volume)


@router.message(RentBox.volume, F.text.in_(["Маленький", "Средний", "Большой"]))
async def process_volume_preset(message: types.Message, state: FSMContext):
    await state.update_data(volume=message.text)
    await show_boxes(message, state)


@router.message(RentBox.volume, F.text.in_(["Отправить список", "Отправить фото"]))
async def process_volume_custom(message: types.Message, state: FSMContext):
    if message.text == "Отправить список":
        await message.answer(
            "Пожалуйста, опишите перечень вещей (например: диван, холодильник, 10 коробок):"
        )
    else:
        await message.answer(
            "Пожалуйста, отправьте фото ваших вещей (можно несколько):"
        )
    await state.set_state(RentBox.volume)


@router.message(RentBox.volume)
async def process_volume_text(message: types.Message, state: FSMContext):
    await state.update_data(volume=message.text)
    await show_boxes(message, state)


async def show_boxes(message: types.Message, state: FSMContext):
    data = await state.get_data()
    delivery = data.get("delivery_method", "Привезу сам")
    
    text = "Расчёт стоимости аренды бокса:\n\n"
    text += "Способ доставки: "
    if delivery == "Привезу сам":
        text += "Самовывоз (скидка 20%)\n\n"
    else:
        text += "Вывоз силами склада\n\n"
    
    text += "Доступные боксы:\n\n"
    
    for box in BOXES:
        price = box["price_per_month"]
        if delivery == "Закажите вывоз":
            price_text = f"{price} ₽/мес"
        else:
            discounted_price = int(price * DELIVERY_SETTINGS["self_delivery_discount"])
            price_text = f"{discounted_price} ₽/мес {price} ₽ (со скидкой)"
        
        text += (
            f"▫️ {box['name']}\n"
            f"   Размер: {box['size']}\n"
            f"   Габариты: {box['dimensions']}\n"
            f"   Цена: {price_text}\n"
            f"   Описание: {box['description']}\n\n"
        )

    text += "Выберите бокс из списка ниже:"
    await message.answer(text, reply_markup=generate_boxes_kb())


@router.callback_query(F.data.startswith("select_box_"))
async def process_select_box(callback: types.CallbackQuery, state: FSMContext):
    box_id = callback.data.replace("select_box_", "")
    box = next((b for b in BOXES if b["id"] == box_id), None)
    
    if box:
        await state.update_data(selected_box=box)
        
        data = await state.get_data()
        delivery = data.get("delivery_method", "Привезу сам")
        price = box["price_per_month"]
        
        if delivery == "Привезу сам":
            price = int(price * DELIVERY_SETTINGS["self_delivery_discount"])
            price_note = f"{price} ₽/мес (со скидкой за самовывоз)"
        else:
            price_note = f"{price} ₽/мес"
        
        await callback.message.answer(
            f"Вы выбрали: {box['name']}\n"
            f"Размер: {box['size']}\n"
            f"Габариты: {box['dimensions']}\n"
            f"Стоимость: {price_note}\n\n"
            f"Описание: {box['description']}\n\n"
            "Подтвердите выбор или вернитесь назад:",
            reply_markup=generate_confirm_kb()
        )
    await callback.answer()


@router.callback_query(F.data == "confirm_box")
async def process_confirm_box(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Пожалуйста, оставьте ваш контактный номер телефона для связи:\n"
        "(Например: +7 918 123-45-67)"
    )
    await callback.answer()
    await state.set_state(RentBox.contact)


@router.message(RentBox.contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact = message.text
    await state.update_data(contact=contact)
    
    data = await state.get_data()
    box = data.get("selected_box", {})
    delivery = data.get("delivery_method", "Привезу сам")
    address = data.get("address", "Не указан")
    volume = data.get("volume", "Не указан")
    
    price = box.get("price_per_month", 0)
    if delivery == "Привезу сам":
        price = int(price * DELIVERY_SETTINGS["self_delivery_discount"])

    summary = (
        "Заявка на аренду бокса:\n\n"
        f"Бокс: {box.get('name', 'Не выбран')} ({box.get('size', '')})\n"
        f"Стоимость: {price} ₽/мес\n"
        f"Способ доставки: {delivery}\n"
        f"Адрес: {address}\n"
        f"Объём: {volume}\n"
        f"Телефон: {contact}\n\n"
        "Ваша заявка отправлена! Наш менеджер свяжется с вами в ближайшее время."
    )

    await message.answer(summary)
    # Получаем пользователяз
    user = await get_or_create_user(message.from_user.id)
    # Создаём заказ в БД
    await create_order(
        user_id=user.id,
        volume=volume,
        delivery_type=delivery,
        phone=contact,
        estimated_price=price,
        address=address
    )

    manager_id = DB.get("meta", {}).get("manager_telegram_id")
    if manager_id:
        try:
            await message.bot.send_message(
                manager_id,
                f"Новая заявка на аренду!\n\n{summary}"
            )
        except Exception:
            pass

    await state.clear()


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