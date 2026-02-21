from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from keyboards.box import (
    generate_delivery_method_kb,
    generate_delivery_method_for_measurements_kb,
    generate_boxes_kb,
    generate_confirm_kb,
    generate_request_contact_kb
)
from decouple import config
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
        "Замеры будут произведены при вывозе ваших вещей\n\n"
        "Специалист приедет к вам, оценит объём и поможет подобрать оптимальный размер бокса."
        reply_markup=generate_delivery_method_for_measurements_kb()
    )

    await state.update_data(selected_box=None, need_measurements=True)
    await state.set_state(RentBox.delivery_method)
    await callback.answer()


@router.message(RentBox.delivery_method, F.text.in_(["Привезу сам", "Закажите самовывоз"]))
async def process_delivery_method(message: types.Message, state: FSMContext):
    await state.update_data(delivery_method=message.text)
    await message.answer(
        "Укажите адрес (город, улица, дом):",
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
    
    data = await state.get_data()
    box = data.get("selected_box") or {}
    delivery = data.get("delivery_method", "Привезу сам")
    address = data.get("address", "Не указан")
    need_measurements = data.get("need_measurements", False)

    if need_measurements:
        volume_text = "Требуются замеры"
        price = 0
        price_text = "Будет определено после замеров"
    else:
        volume_text = f"{box.get('name', '')} ({box.get('size', '')})"
        price = box.get("price_per_month", 0)
        if delivery == "Привезу сам":
            price = int(price * DELIVERY_SETTINGS["self_delivery_discount"])
        price_text = f"{price} ₽/мес"

    summary = (
        "Заявка на аренду бокса:\n\n"
        f"Бокс: {volume_text}\n"
        f"Стоимость: {price_text}\n"
        f"Способ доставки: {delivery}\n"
        f"Адрес: {address}\n"
        f"Телефон: {contact}\n\n"
        "Ваша заявка отправлена! Наш менеджер свяжется с вами в ближайшее время."
    )

    await message.answer(summary)

    user = await get_or_create_user(message.from_user.id)

    await create_order(
        user_id=user.id,
        volume=volume_text,
        delivery_type=delivery,
        phone=contact,
        estimated_price=price,
        address=address
    )

    manager_id = config('ADMIN_CHAT_ID')
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