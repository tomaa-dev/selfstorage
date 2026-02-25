import asyncio
from datetime import datetime
from database.repository import check_and_notify_expiring_orders, mark_and_notify_expired_orders
from decouple import config
import logging


logger = logging.getLogger(__name__)


async def run_daily_checks():
    logger.info("Запуск ежедневной проверки заказов...")
    
    try:
        await check_and_notify_expiring_orders()
        logger.info("Напоминания отправлены")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}")

    try:
        expired_count = await mark_and_notify_expired_orders()
        if expired_count > 0:
            logger.info(f"Просрочено {expired_count} заказов")
    except Exception as e:
        logger.error(f"Ошибка при проверке просроченных заказов: {e}")


def start_scheduler():
    import aioschedule as schedule
    import time
    
    async def scheduler():
        while True:
            await schedule.run_pending()
            await asyncio.sleep(60)

    schedule.every().day.at("09:00").do(lambda: asyncio.create_task(run_daily_checks()))
    
    return scheduler