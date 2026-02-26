import asyncio
from decouple import config
from aiogram import Bot, Dispatcher
from handlers import register_routes
from database.init_db import init_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler


TG_TOKEN = config('TELEGRAM_TOKEN')
scheduler = AsyncIOScheduler()


async def run_daily_checks():
    from database.repository import (
        check_and_notify_expiring_orders, 
        mark_and_notify_expired_orders,
        mark_expired_orders_auto,
        check_and_notify_overdue_orders
    )
    
    print("Запуск проверки заказов...")
    
    try:
        await check_and_notify_expiring_orders()
        print("Напоминания об истекающих заказах отправлены")
    except Exception as e:
        print(f"Ошибка при отправке напоминаний: {e}")

    try:
        await mark_expired_orders_auto()
        print("Просроченные заказы помечены")
    except Exception as e:
        print(f"Ошибка при пометке просроченных заказов: {e}")

    try:
        expired_count = await mark_and_notify_expired_orders()
        if expired_count > 0:
            print(f"Обработано просроченных заказов: {expired_count}")
    except Exception as e:
        print(f"Ошибка при обработке просроченных заказов: {e}")

    try:
        await check_and_notify_overdue_orders()
        print("Уведомления о просроченных заказах отправлены")
    except Exception as e:
        print(f"Ошибка при отправке уведомлений о просрочке: {e}")
    
    print("Ежедневная проверка завершена")


async def main():
    bot = Bot(token=TG_TOKEN)
    dp = Dispatcher()

    await init_db()

    scheduler.add_job(
        run_daily_checks,
        trigger='cron',
        hour=9,
        minute=0,
        id='daily_check'
    )
    scheduler.start()
    print("Планировщик запущен (проверка каждый день в 9:00)")


    register_routes(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен!")