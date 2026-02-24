import datetime
from typing import Optional, Dict, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database.models import User, Order, PromoCode


class TariffType:
    """Типы тарифов хранения"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


def validate_promo_code_db(
    session: Session,
    promo_code: str,
    check_date: datetime.date = None
) -> Tuple[bool, str, Optional[int]]:

    if not promo_code:
        return False, "Промокод не указан", None

    promo_code = promo_code.upper().strip()

    if check_date is None:
        check_date = datetime.date.today()

    # Поиск промокода в БД
    promocode_obj = session.query(PromoCode).filter(
        PromoCode.code == promo_code
    ).first()

    if not promocode_obj:
        return False, f"Промокод '{promo_code}' не найден", None

    # Проверка активности
    if not promocode_obj.is_active:
        return False, f"Промокод '{promo_code}' деактивирован", None

    # Проверка по датам
    if promocode_obj.active_from and check_date < promocode_obj.active_from:
        return False, f"Промокод '{promo_code}' ещё не активен", None

    if promocode_obj.active_to and check_date > promocode_obj.active_to:
        return False, f"Промокод '{promo_code}' истёк", None

    return True, f"Промокод '{promo_code}' валиден", promocode_obj.discount_percent


def apply_promo_code_to_price(
    session: Session,
    price: float,
    promo_code: str,
    check_date: datetime.date = None
) -> Tuple[float, str, Optional[int]]:

    is_valid, message, discount = validate_promo_code_db(session, promo_code, check_date)

    if not is_valid or discount is None:
        return price, message, None

    discounted_price = price * (100 - discount) / 100

    discounted_price = round(discounted_price, 2)

    return discounted_price, f"Применена скидка {discount}%", discount


def calculate_storage_cost_db(
    session: Session,
    storage_days: int,
    width: float,
    height: float,
    depth: float,
    tariff: str,
    promo_code: str = None,
    check_date: datetime.date = None,
    user_id: int = None
) -> Dict[str, Union[float, str, int, bool, None]]:

    if storage_days <= 0:
        return {
            "success": False,
            "error": "Количество дней должно быть положительным числом"
        }

    if any(dim <= 0 for dim in [width, height, depth]):
        return {
            "success": False,
            "error": "Габариты должны быть положительными числами"
        }

    volume = width * height * depth

    tariff_rates = {
        TariffType.SMALL: 10.0,
        TariffType.MEDIUM: 20.0,
        TariffType.LARGE: 35.0
    }

    # Нормализация тарифа
    tariff = tariff.lower()
    if tariff not in tariff_rates:
        return {
            "success": False,
            "error": f"Неизвестный тариф: {tariff}. Допустимые: маленький, средний, большой"
        }

    # Расчёт базовой стоимости
    daily_rate = tariff_rates[tariff]
    base_cost = volume * daily_rate * storage_days

    base_cost = round(base_cost, 2)

    result = {
        "success": True,
        "storage_days": storage_days,
        "volume_m3": round(volume, 3),
        "tariff": tariff,
        "daily_rate": daily_rate,
        "base_cost": base_cost,
        "promo_code_applied": False,
        "discount_percent": None,
        "discount_amount": 0,
        "final_cost": base_cost,
        "message": "Стоимость рассчитана без промокода"
    }

    # Применение промокода, если указан
    if promo_code:
        is_valid, promo_message, discount = validate_promo_code_db(
            session, promo_code, check_date
        )

        if is_valid and discount is not None:
            discount_amount = base_cost * discount / 100
            final_cost = base_cost - discount_amount

            result.update({
                "promo_code_applied": True,
                "promo_code": promo_code.upper(),
                "discount_percent": discount,
                "discount_amount": round(discount_amount, 2),
                "final_cost": round(final_cost, 2),
                "message": f"Применена скидка {discount}% по промокоду {promo_code.upper()}"
            })
        else:
            result["message"] = f"Промокод не применён: {promo_message}"

    return result


def create_order_from_calculation(
    session: Session,
    user_id: int,
    calculation_result: Dict,
    delivery_type: str,
    address: str = None,
    preferred_time: str = None,
    phone: str = None
) -> Optional[Order]:

    if not calculation_result.get("success", False):
        return None

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    if not phone:
        phone = user.phone

    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=calculation_result["storage_days"])

    # Создаём заказ
    order = Order(
        user_id=user_id,
        volume=f"{calculation_result['volume_m3']} м³",
        delivery_type=delivery_type,
        address=address,
        preferred_time=preferred_time,
        phone=phone,
        estimated_price=int(calculation_result["final_cost"]),
        final_price=None,  # Будет заполнено после замеров
        status="CREATED",
        start_date=start_date,
        end_date=end_date
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    return order


def get_user_orders_with_promo_stats(
    session: Session,
    user_id: int
) -> Dict:

    orders = session.query(Order).filter(Order.user_id == user_id).all()

    if not orders:
        return {
            "user_id": user_id,
            "total_orders": 0,
            "total_spent": 0,
            "average_order_value": 0,
            "orders": []
        }

    total_spent = sum(order.final_price or order.estimated_price for order in orders)

    orders_info = []
    for order in orders:
        orders_info.append({
            "id": order.id,
            "volume": order.volume,
            "estimated_price": order.estimated_price,
            "final_price": order.final_price,
            "status": order.status,
            "start_date": order.start_date.isoformat() if order.start_date else None,
            "end_date": order.end_date.isoformat() if order.end_date else None,
            "delivery_type": order.delivery_type
        })

    return {
        "user_id": user_id,
        "total_orders": len(orders),
        "total_spent": total_spent,
        "average_order_value": round(total_spent / len(orders), 2),
        "orders": orders_info
    }


def get_active_promocodes(
    session: Session,
    check_date: datetime.date = None
) -> list:

    if check_date is None:
        check_date = datetime.date.today()

    promocodes = session.query(PromoCode).filter(
        PromoCode.is_active == True,
        and_(
            (PromoCode.active_from <= check_date) | (PromoCode.active_from.is_(None)),
            (PromoCode.active_to >= check_date) | (PromoCode.active_to.is_(None))
        )
    ).all()

    return [
        {
            "code": p.code,
            "discount_percent": p.discount_percent,
            "active_from": p.active_from.isoformat() if p.active_from else None,
            "active_to": p.active_to.isoformat() if p.active_to else None
        }
        for p in promocodes
    ]
