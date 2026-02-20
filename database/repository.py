import datetime
from sqlalchemy import select, update
from database.session import async_session
from database.models import User, Order, PromoCode

async def get_or_create_user(telegram_id: int): # поверка есть ли пользователь или нет
    async with async_session() as session:

        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            user = User(telegram_id=telegram_id)

            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

async def create_order(  # создание заказа
    user_id: int,
    volume: str,
    delivery_type: str,
    phone: str,
    estimated_price: int,
    address: str | None = None,
    preferred_time: str | None = None,
):
    async with async_session() as session:

        order = Order(
            user_id=user_id,
            volume=volume,
            delivery_type=delivery_type,
            phone=phone,
            estimated_price=estimated_price,
            address=address,
            preferred_time=preferred_time,
            status="CREATED"
        )

        session.add(order)
        await session.commit()
        await session.refresh(order)

        return order


async def get_order_by_id(order_id: int): # получить заказ по ID
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()


async def get_user_orders(user_id: int): # получить заказы пользователя
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.user_id == user_id)
        )
        return result.scalars().all()

async def get_valid_promo(code: str): # проверка промокода
    today = datetime.date.today()

    async with async_session() as session:
        result = await session.execute(
            select(PromoCode).where(
                PromoCode.code == code,
                PromoCode.is_active == True,
                (PromoCode.active_from == None) | (PromoCode.active_from <= today),
                (PromoCode.active_to == None) | (PromoCode.active_to >= today),
            )
        )

        return result.scalar_one_or_none()

# админка

async def get_all_orders():  # получить все заказы
    async with async_session() as session:
        result = await session.execute(
            select(Order).order_by(Order.id.desc())
        )
        return result.scalars().all()


async def get_overdue_orders(): # просроченые заказы
    today = datetime.date.today()

    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                Order.end_date < today,
                Order.status == "IN_STORAGE"
            )
        )
        return result.scalars().all()


async def get_all_phones(): # получить телефоны пользователей
    async with async_session() as session:
        result = await session.execute(
            select(Order.id, Order.phone)
        )
        return result.all()


async def update_order_status(order_id: int, new_status: str):  # изменение статуса заказа
    async with async_session() as session:
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=new_status)
        )

        await session.commit()