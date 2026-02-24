import datetime
from sqlalchemy import select
from database.models import Base, PromoCode
from database.session import engine, async_session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # добавляем дефолтные промокоды (если их еще нет)
    async with async_session() as session:
        await _ensure_promo(session, "storage2022", 20,
                            datetime.date(2026, 2, 1),
                            datetime.date(2026, 3, 31))
        await _ensure_promo(session, "storage15", 15,
                            datetime.date(2026, 11, 1),
                            datetime.date(2026, 4, 30))
        await session.commit()

async def _ensure_promo(session, code, percent, active_from, active_to):
    result = await session.execute(select(PromoCode).where(PromoCode.code == code))
    promo = result.scalar_one_or_none()
    if not promo:
        session.add(PromoCode(
            code=code,
            discount_percent=percent,
            active_from=active_from,
            active_to=active_to,
            is_active=True
        ))