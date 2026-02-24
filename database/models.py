import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey


class Base(DeclarativeBase):
    pass


class User(Base):  # пользователи
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)  # ID пользователя
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)  # ID пользователя telegram
    created_at: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)  # дата регистрации пользователя


class Order(Base):  # заказы
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)  # ID заказа
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # связь пользователя с заказом
    email: Mapped[int] = mapped_column(String(50), primary_key=True) # почта
    fio: Mapped[str] = mapped_column(String(20), nullable=True) # фамилия имя отчество
    promo_code: Mapped[str] = mapped_column(String(50), nullable=True)

    volume: Mapped[str] = mapped_column(String(50))  # объем заказа
    delivery_type: Mapped[str] = mapped_column(String(20))  # способ доставки
    address: Mapped[str] = mapped_column(String(255), nullable=True)  # адрес доставки
    preferred_time: Mapped[str] = mapped_column(String(100), nullable=True)  # предпочитаемое время

    phone: Mapped[str] = mapped_column(String(20))  # телефон заказа

    estimated_price: Mapped[int] = mapped_column(Integer)  # цена до замеров
    final_price: Mapped[int] = mapped_column(Integer, nullable=True)  # финальная цена после замеров

    reserve_until: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)  # резерв бокса

    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=True)  # дата начала хранения
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=True)  # дата окончания хранения


class PromoCode(Base):  # промокоды
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)  # ID промокода
    code: Mapped[str] = mapped_column(String(50), unique=True)  # промокод
    discount_percent: Mapped[int] = mapped_column(Integer)  # процент скидки
    active_from: Mapped[datetime.date] = mapped_column(Date, nullable=True) # дата начала промокода
    active_to: Mapped[datetime.date] = mapped_column(Date, nullable=True) # дата оконччания промокода
    is_active: Mapped[bool] = mapped_column(default=True)  # активность промокода
    is_advertising: Mapped[bool] = mapped_column(default=False) # реклама
    usage_count: Mapped[int] = mapped_column(default=0) # количество использований
