from aiogram import Router, types
from aiogram.filters import Command
from keyboards.menu import main_menu_kb
from aiogram.types import FSInputFile
from config import PD_PDF_PATH
from database.repository import get_or_create_user


router = Router()


@router.message(Command("start"))
async def start_bot(message: types.Message):
    user, is_new = await get_or_create_user(message.from_user.id)

    pdf = FSInputFile(PD_PDF_PATH)

    await message.answer_document(
        document=pdf,
        caption=(
            "Перед началом работы с ботом ознакомьтесь, пожалуйста,\nс согласием на обработку персональных данных."
        )
    )

    await message.answer(
        f"{message.from_user.full_name}, Вас приветствует сервис SelfStorage! Помогаю удобно хранить вещи в небольших боксах.\n"
        "Примеры использования:\n"
        "- Хранение сезонной техники: снегоходы, лыжи, сноуборды;\n"
        "- Хранение вещей между этапами переезда;\n"
        "- Уборка дома: крупная мебель или техника, чтобы освободить пространство;\n"
        "- Хранение вещей «на память».\n"
        "Выберете нужное меню снизу\n",
        reply_markup=main_menu_kb(message.from_user.id)
    )