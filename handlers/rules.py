from aiogram import F, Router, types
from keyboards.rules import generate_rules, generate_prohibited_kb, generate_allowed_kb
from decouple import config
from config import PROHIBITED_KEYWORDS, ALLOWED_KEYWORDS, BOXES, MANAGER_PHONE
from aiogram.types import CallbackQuery
from handlers.box import RentBox


router = Router()


@router.message(F.text == "Правила хранения")
async def rule(message: types.Message):
    text = (
        "Правила хранения — кратко и важно:\n\n"
        "Разрешено:\n"
        "- Мебель, бытовая техника (обезвоженная/обесточенная), одежда, коробки, книги, документы,\n"
        "- Спортивный инвентарь (лыжи, сноуборд, велосипеды), аккуратно упакованный инструмент.\n\n"
        "Запрещено:\n"
        "- Горючие и легковоспламеняющиеся жидкости (бензин, растворители, лак), газовые баллоны,\n"
        "- Ядовитые, коррозионные и радиоактивные вещества, живые животные,\n"
        "- Вещества, требующие специальных условий хранения (холодильное, химически активное).\n\n"
        "Условия хранения:\n"
        "- Сухое, вентилируемое помещение; рекомендация: температура +5…+25°C;\n"
        "- Относительная влажность: по возможности ниже 60% (избегайте сырости);\n"
        "- Электроприборы — подготовьте к хранению (сливать топливо, отсоединить аккумуляторы).\n\n"
        "FAQ — можно ли хранить жидкости?\n"
        "- Небольшие бытовые герметичные емкости (вода в плотно закрытой таре) обычно допустимы.\n"
        "- Горючие, токсичные или коррозионные жидкости запрещены — их хранение опасно.\n\n"
        "Чтобы проверить конкретный предмет, просто напишите его название (например: «бензин», «диван», «лыжи»)."
    )
    await message.answer(text, reply_markup=generate_rules())


@router.message(RentBox.volume)
async def check_item(message: types.Message):
    text = message.text.lower()
    prohibited_found = [kw for kw in PROHIBITED_KEYWORDS if kw.lower() in text]
    if prohibited_found:
        reasons = {
            "бензин": "горючая жидкость, пожароопасно",
            "дизель": "горючая жидкость, пожароопасно",
            "солярка": "горючая жидкость, пожароопасно",
            "керосин": "горючая жидкость, пожароопасно",
            "растворитель": "легковоспламеняющаяся жидкость",
            "лак": "легковоспламеняющаяся жидкость",
            "краска": "легковоспламеняющаяся жидкость",
            "газовый баллон": "взрывоопасно",
            "баллон": "взрывоопасно",
            "взрывчат": "взрывоопасно",
            "яд": "ядовито",
            "ядовит": "ядовито",
            "радиоактив": "радиоактивно",
            "радиация": "радиоактивно",
            "хлор": "коррозионно и токсично",
            "кислота": "коррозионно",
            "щелочь": "коррозионно",
            "корроз": "коррозионно",
            "живот": "живые организмы запрещены",
            "живые": "живые организмы запрещены",
            "органика (гнилостная)": "гнилостная органика",
            "легковоспламеняющиеся": "легковоспламеняющиеся вещества",
            "огнеопасно": "огнеопасно"
        }
        reason = reasons.get(prohibited_found[0], "запрещено по правилам безопасности")
        await message.answer(
            f"Этот предмет запрещён к хранению по причине: {reason}. Предлагаем варианты: утилизация или связаться с оператором.",
            reply_markup=generate_prohibited_kb()
        )
        return

    allowed_found = [kw for kw in ALLOWED_KEYWORDS if kw.lower() in text]
    if allowed_found:
        await message.answer(
            "Этот предмет разрешён к хранению. Хотите подобрать бокс?",
            reply_markup=generate_allowed_kb()
        )
        return
    
    await message.answer(
        "Не уверен, разрешён ли этот предмет. Свяжитесь с оператором для уточнения.",
        reply_markup=generate_rules()
    )


@router.callback_query(F.data == "pick_box")
async def pick_box(callback: CallbackQuery):
    text = "Доступные боксы для аренды:\n\n"
    
    for box in BOXES:
        text += (
            f"{box['name']}\n"
            f"Размер: {box['size']} ({box['dimensions']})\n"
            f"Цена: {box['price_per_month']} руб/мес\n"
            f"Описание: {box['description']}\n\n"
        )
    
    text += "Чтобы забронировать, нажмите 'Связаться с оператором'."
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "contact_operator")
async def contact_operator(callback: CallbackQuery):
    tg_link = f"tg://user?id={config(ADMIN_CHAT_ID)}"
    
    text = (
        "Связь с оператором\n\n"
        f"Телефон: <a href=\"tel:{MANAGER_PHONE}\">{MANAGER_PHONE}</a>\n"
        f"Telegram: <a href=\"{tg_link}\">Написать менеджеру</a>\n\n"
        "Наш менеджер поможет подобрать бокс, ответить на вопросы по условиям хранения или оформить заказ."
    )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dispose_help")
async def dispose_help(callback: CallbackQuery):
    await callback.message.answer(
        "Для утилизации крупногабаритных вещей мы рекомендуем обратиться в специализированные пункты приема металлолома или ЖЭК (вывоз мусора).\n"
        "Если вам нужна помощь в поиске — оператор подскажет контакты.",
        reply_markup=generate_prohibited_kb()
    )
    await callback.answer()