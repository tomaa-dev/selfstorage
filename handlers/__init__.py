from aiogram import Dispatcher
from handlers.start import router as start_router
from handlers.info import router as info_router
from handlers.rules import router as rules_router
from handlers.box import router as box_router
from handlers.orders import router as orders_router
from handlers.admin import router as admin_router


def register_routes(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(info_router)
    dp.include_router(box_router)
    dp.include_router(admin_router)
    dp.include_router(orders_router)
    dp.include_router(rules_router)
    