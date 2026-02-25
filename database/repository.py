import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select, update, and_
from database.session import async_session
from database.models import User, Order, PromoCode
from sqlalchemy import func
from decouple import config


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

async def get_orders_for_admin_list():
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                Order.status.in_(["CREATED", "PAID"])
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
                    Order.end_date >= func.current_date()
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

async def admin_check_expired_orders() -> int:
    today = datetime.date.today()

    expired_orders = await get_expired_orders()

    processed = 0
    for order in expired_orders:
        if not order.end_date:
            continue

        if order.end_date < today:
            await mark_order_expired(order.id)
            await notify_order_expired(order.id)
            processed += 1

    return processed

async def get_expired_status_orders():
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.status == "EXPIRED")
        )
        return result.scalars().all()

async def get_all_storage_orders():
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.status.in_(["IN_STORAGE", "EXPIRED"]))
        )
        return result.scalars().all()

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


async def send_real_email(email: str, subject: str, message: str) -> bool:
    if not email:
        return False

    smtp_host = config('SMTP_HOST', default='smtp.gmail.com')
    smtp_port = config('SMTP_PORT', default=587, cast=int)
    smtp_user = config('SMTP_USER', default='')
    smtp_password = config('SMTP_PASSWORD', default='')
    from_email = config('FROM_EMAIL', default='noreply@selfstorage.ru')

    if not smtp_user or not smtp_password:
        print(f"[ЗАГЛУШКА] EMAIL to {email}:")
        print(f"Subject: {subject}")
        print(f"Message: {message[:100]}...")
        return True
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"EMAIL отправлен: {email}")
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        print(f"[ЗАГЛУШКА] EMAIL to {email}:")
        print(f"Subject: {subject}")
        return False


async def notify_order_expiring_soon(order_id: int, days_left: int):
    order = await get_order_by_id(order_id)
    if order and order.email:
        await send_real_email(
            email=order.email,
            subject="Срок хранения скоро истекает - SelfStorage",
            message=f"""Уважаемый {order.fio or 'клиент'}!

   Напоминаем, что срок хранения вашего заказа №{order_id} истекает через {days_left} дней.

   Детали заказа:
   Бокс: {order.volume}
   Дата окончания: {order.end_date}
   Телефон: {order.phone}

   Если вы хотите продлить аренду или забрать вещи, свяжитесь с нами:
   Телефон: +7-918-714-58-30
   Telegram: @selfstorage_bot

С уважением,
Команда SelfStorage
"""
        )


async def notify_order_expired(order_id: int):
    order = await get_order_by_id(order_id)
    if order and order.email:
        await send_real_email(
            email=order.email,
            subject="Срок хранения истёк - SelfStorage",
            message=f"""Уважаемый {order.fio or 'клиент'}!

   Срок хранения вашего заказа №{order_id} истёк.

   Детали заказа:
   Бокс: {order.volume}
   Дата окончания: {order.end_date}
   Телефон: {order.phone}

   Пожалуйста, свяжитесь с нами для продления аренды или вывоза вещей:
   Телефон: +7-918-714-58-30
   Telegram: @selfstorage_bot

С уважением,
Команда SelfStorage
"""
        )


async def notify_order_delivered(order_id: int):
    """Уведомить о доставке и приеме на склад"""
    order = await get_order_by_id(order_id)
    if order and order.email:
        await send_real_email(
            email=order.email,
            subject="Ваш заказ принят на склад - SelfStorage",
            message=f"""Уважаемый {order.fio or 'клиент'}!

   Ваш заказ №{order_id} успешно доставлен и принят на склад!

   Детали заказа:
   Бокс: {order.volume}
   Дата начала: {order.start_date}
   Дата окончания: {order.end_date}
   Сумма: {order.estimated_price} ₽

   Ваши вещи находятся на складе по адресу:
   г. Москва, ул. Складская, д. 15

   В случае вопросов свяжитесь с нами:
   Телефон: +7-918-714-58-30
   Telegram: @selfstorage_bot

С уважением,
Команда SelfStorage
"""
        )


async def check_and_notify_expiring_orders():
    today = datetime.date.today()
    orders = await get_orders_in_storage()
    
    for order in orders:
        days_left = (order.end_date - today).days

        if days_left in [30, 14, 7, 3, 1]:
            await notify_order_expiring_soon(order.id, days_left)


async def mark_and_notify_expired_orders():
    expired_orders = await get_expired_orders()
    
    for order in expired_orders:
        await mark_order_expired(order.id)
        await notify_order_expired(order.id)
    
    return len(expired_orders)