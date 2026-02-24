import datetime
from sqlalchemy import select, update, and_
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
    email: str | None = None,
    is_delivery_required: bool = False
):
    async with async_session() as session:
        order = Order(
            user_id=user_id,
            fio=fio,
            email=email,
            volume=volume,
            delivery_type=delivery_type,
            phone=phone,
            estimated_price=estimated_price,
            address=address,
            reserve_until=reserve_until,
            start_date=start_date,
            end_date=end_date,
            promo_code=promo_code,
            status="CREATED",
            is_delivery_required=is_delivery_required
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


async def get_orders_for_delivery():
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                and_(
                    Order.is_delivery_required == True,
                    Order.is_delivered == False,
                    Order.status == "PAID"
                )
            ).order_by(Order.id.desc())
        )
        return result.scalars().all()


async def get_orders_in_storage():
    today = datetime.date.today()
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                and_(
                    Order.status == "IN_STORAGE",
                    Order.end_date >= today
                )
            ).order_by(Order.end_date.asc())
        )
        return result.scalars().all()


async def get_expired_orders():
    today = datetime.date.today()
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                and_(
                    Order.status == "IN_STORAGE",
                    Order.end_date < today
                )
            ).order_by(Order.end_date.asc())
        )
        return result.scalars().all()


async def update_order(order_id: int, **kwargs):
    from sqlalchemy import update
    async with async_session() as session:
        await session.execute(
            update(Order).where(Order.id == order_id).values(**kwargs)
        )
        await session.commit()


async def mark_order_paid(order_id: int):
    await update_order(order_id, status="PAID", start_date=datetime.date.today())


async def mark_order_in_storage(order_id: int):
    await update_order(order_id, status="IN_STORAGE")


async def mark_order_delivered(order_id: int):
    await update_order(order_id, is_delivered=True)


async def mark_order_completed(order_id: int):
    await update_order(order_id, status="COMPLETED")


async def mark_order_expired(order_id: int):
    await update_order(order_id, status="EXPIRED")


async def get_all_phones():
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


async def send_email_notification(order_id: int, subject: str, message: str):
    order = await get_order_by_id(order_id)
    if order and order.email:
        print(f"📧 EMAIL to {order.email}:")
        print(f"   Subject: {subject}")
        print(f"   Message: {message}")
        # Здесь должна быть реальная отправка письма
        return True
    return False


async def notify_order_expiring_soon(order_id: int, days_left: int):
    order = await get_order_by_id(order_id)
    if order:
        await send_email_notification(
            order_id,
            subject="Срок хранения скоро истекает",
            message=f"Уважаемый {order.fio or 'клиент'}!\n\n"
                   f"Ваш заказ №{order_id} на складе истекает через {days_left} дней.\n"
                   f"Дата окончания: {order.end_date}\n\n"
                   f"Если хотите продлить аренду, свяжитесь с нами."
        )


async def notify_order_expired(order_id: int):
    order = await get_order_by_id(order_id)
    if order:
        await send_email_notification(
            order_id,
            subject="Срок хранения истёк",
            message=f"Уважаемый {order.fio or 'клиент'}!\n\n"
                   f"Срок хранения вашего заказа №{order_id} истёк.\n"
                   f"Пожалуйста, заберите вещи или свяжитесь с нами для продления аренды."
        )