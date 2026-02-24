import datetime
from sqlalchemy import select, update
from database.session import async_session
from database.models import User, Order, PromoCode
from sqlalchemy import func

async def get_or_create_user(telegram_id: int): # поверка есть ли пользователь или нет
    async with async_session() as session:

        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )

        user = result.scalar_one_or_none()

        if user:
            return user, False

        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user, True

async def create_order(  # создание заказа
    user_id: int,
    fio: str,
    volume: str,
    delivery_type: str,
    phone: str,
    estimated_price: int,
    address: str | None = None,
    reserve_until: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    promo_code: str | None = None,
):
    async with async_session() as session:

        order = Order(
            user_id=user_id,
            fio=fio,
            volume=volume,
            delivery_type=delivery_type,
            phone=phone,
            estimated_price=estimated_price,
            address=address,
            reserve_until=reserve_until,
            start_date=start_date,
            end_date=end_date,
            promo_code=promo_code
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


async def get_all_phones(): # получить телефоны пользователей
    async with async_session() as session:
        result = await session.execute(
            select(Order.id, Order.phone)
        )
        return result.all()

# промокод
async def create_promo(code: str, discount_percent: int, active_from=None, active_to=None):
    async with async_session() as session:
        promo = PromoCode(
            code=code,
            discount_percent=discount_percent,
            is_active=True,
            active_from=active_from,
            active_to=active_to
        )
        session.add(promo)
        await session.commit()


async def get_all_promo():
    async with async_session() as session:
        result = await session.execute(select(PromoCode).order_by(PromoCode.id.desc()))
        return result.scalars().all()


async def set_promo_active(code: str, active: bool):
    async with async_session() as session:
        await session.execute(
            update(PromoCode)
            .where(PromoCode.code == code)
            .values(is_active=active)
        )
        await session.commit()


async def count_orders_by_promo(code: str) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Order.id)).where(Order.promo_code == code)
        )
        return result.scalar_one()

async def increase_promo_usage(code: str):
    async with async_session() as session:
        await session.execute(
            update(PromoCode)
            .where(PromoCode.code == code)
            .values(usage_count=PromoCode.usage_count + 1)
        )
        await session.commit()
