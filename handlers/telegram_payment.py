import logging
from environs import Env
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

env = Env()
env.read_env()
BOT_TOKEN = env.str('BOT_TOKEN') # Вставьте токен бота от BotFather
PAYMENT_PROVIDER_TOKEN = '1744374395:TEST:a078915445160dfb92d0'  # Вставьте тестовый токен провайдера

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Отправьте /pay для тестовой оплаты')


async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat_id

        # ВАЖНО: Цена в КОПЕЙКАХ (100 рублей = 100 * 100 = 10000 копеек)
        # Но передаём как строку или список словарей
        prices = [
            {
                'label': 'Тестовый товар',
                'amount': 10000  # 100 рублей в копейках
            }
        ]

        await context.bot.send_invoice(
            chat_id=chat_id,
            title='Тестовый товар',
            description='Описание тестового товара для оплаты',
            payload='test-payload',
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency='RUB',
            prices=prices,
            need_name=True,
            need_email=True,
            need_phone_number=False,
            need_shipping_address=False,
            is_flexible=False,
            # Важно: максимальная сумма не должна превышать лимиты
            max_tip_amount=0,
            suggested_tip_amounts=[]
        )
        logging.info(f"Инвойс отправлен пользователю {chat_id}")

    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    logging.info(f"Pre-checkout запрос от {query.from_user.id}")

    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('✅ Оплата прошла успешно! Спасибо за покупку!')


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('pay', pay))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.error(f"Ошибка: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(f"Произошла ошибка: {context.error}")

    app.add_error_handler(error_handler)

    print('Бот запущен... Нажмите Ctrl+C для остановки')
    app.run_polling()


if __name__ == '__main__':
    main()