import asyncio
from decouple import config
from aiogram import Bot, Dispatcher
from handlers import register_routes
from database.init_db import init_db


TG_TOKEN = config('TELEGRAM_TOKEN')


async def main():
    bot = Bot(token=TG_TOKEN)
    dp = Dispatcher()

    await init_db()

    register_routes(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен!")