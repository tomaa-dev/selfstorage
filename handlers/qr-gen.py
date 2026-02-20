import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import qrcode
from io import BytesIO
import uuid
from datetime import datetime
from environs import Env


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

env = Env()
env.read_env()
TOKEN = env.str('TG_TOKEN')


orders = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Это тестовый бот для генерации QR-кодов.\n"
        "Нажми /new чтобы создать тестовый заказ и получить QR-код."
    )


async def new_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    order_id = str(uuid.uuid4())[:8] #id заказа из модели
    orders[order_id] = {
        'order_id': order_id,
        'user_id': user_id,
        'items': 'Тестовый товар',
        'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
    }

    #кнопка для получения QR-кода
    keyboard = [[
        InlineKeyboardButton("📱 Получить QR-код", callback_data=f"get_qr_{order_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Заказ №{order_id} создан!\n"
        f"Нажмите кнопку ниже, чтобы получить QR-код для получения заказа.",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("get_qr_"):
        order_id = query.data.replace("get_qr_", "")

        order = orders.get(order_id)

        if not order:
            await query.edit_message_text("❌ Заказ не найден")
            return

        try:
            # Данные для QR-кода
            qr_data = f"ORDER:{order_id}|USER:{order['user_id']}|ITEMS:{order['items']}"

            # Создаем QR-код
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)

            # Создаем изображение
            img = qr.make_image(fill_color="black", back_color="white")

            # Сохраняем в BytesIO для отправки
            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)

            # Отправляем QR-код
            await query.message.reply_photo(
                photo=bio,
                caption=f"✅ Ваш QR-код для заказа №{order_id}\n\n"
                        f"Покажите этот код сотруднику склада."
            )

            # Обновляем сообщение с кнопкой
            await query.edit_message_text(
                f"✅ QR-код для заказа №{order_id} отправлен выше!\n"
                f"Хотите создать еще один заказ? Нажмите /new"
            )

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await query.edit_message_text(f"❌ Ошибка при создании QR-кода: {e}")


async def test_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простая команда для теста генерации QR"""
    try:
        # Простой QR-код с тестовыми данными
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data("https://t.me/test_bot")
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)

        await update.message.reply_photo(
            photo=bio,
            caption="✅ Тестовый QR-код успешно создан!"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


def main():
    app = Application.builder().token(TOKEN).build()

    #обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_order))
    app.add_handler(CommandHandler("test", test_qr))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()