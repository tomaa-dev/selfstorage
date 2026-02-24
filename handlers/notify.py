import datetime
from typing import List, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from database.models import User, Order
from environs import Env


env = Env()
env.read_env()
# Конфигурация email
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 465
SMTP_USERNAME = "CephalonSunraze@yandex.ru"
SMTP_PASSWORD = env.str('MAIL_PASSWORD')
FROM_EMAIL = "CephalonSunraze@yandex.ru"


def send_email_notification(to_email: str, subject: str, message: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False


def get_user_email(user: User) -> str:
    if not user.email:
        print(f"Внимание: У пользователя {user.id} (telegram_id: {user.telegram_id}) не указан email")

        raise ValueError(f"У пользователя {user.id} не указан email для отправки уведомлений")

    return user.email


def check_and_send_rental_notifications(db: Session) -> List[Tuple[int, str]]:
    today = datetime.date.today()
    notifications_sent = []

    active_orders = db.query(Order).filter(
        Order.end_date.isnot(None),
        Order.start_date.isnot(None),
        Order.end_date >= today
    ).all()

    for order in active_orders:
        user = db.query(User).filter(User.id == order.user_id).first()
        if not user:
            continue

        days_until_end = (order.end_date - today).days
        user_email = get_user_email(user)

        if days_until_end == 30:
            subject = "Напоминание об окончании аренды через 30 дней"
            message = f"""
            Уважаемый клиент!

            Напоминаем, что срок аренды вашего бокса заканчивается через 30 дней ({order.end_date.strftime('%d.%m.%Y')}).

            Детали заказа:
            • Номер заказа: {order.id}
            • Объем: {order.volume}
            • Дата окончания: {order.end_date.strftime('%d.%m.%Y')}

            Для продления аренды свяжитесь с нами.

            С уважением,
            Команда selfStorage
            """
            if send_email_notification(user_email, subject, message):
                notifications_sent.append((user.id, "30_days"))

        elif days_until_end == 14:
            subject = "Напоминание об окончании аренды через 14 дней"
            message = f"""
            Уважаемый клиент!

            Напоминаем, что срок аренды вашего бокса заканчивается через 14 дней ({order.end_date.strftime('%d.%m.%Y')}).

            Детали заказа:
            • Номер заказа: {order.id}
            • Объем: {order.volume}
            • Дата окончания: {order.end_date.strftime('%d.%m.%Y')}

            Для продления аренды свяжитесь с нами.

            С уважением,
            Команда selfStorage
            """
            if send_email_notification(user_email, subject, message):
                notifications_sent.append((user.id, "14_days"))

        elif days_until_end == 7:
            subject = "Срочное напоминание об окончании аренды через 7 дней"
            message = f"""
            Уважаемый клиент!

            Срок аренды вашего бокса заканчивается через 7 дней ({order.end_date.strftime('%d.%m.%Y')}).

            Детали заказа:
            • Номер заказа: {order.id}
            • Объем: {order.volume}
            • Дата окончания: {order.end_date.strftime('%d.%m.%Y')}

            Пожалуйста, свяжитесь с нами для продления аренды.

            С уважением,
            Команда selfStorage
            """
            if send_email_notification(user_email, subject, message):
                notifications_sent.append((user.id, "7_days"))

        elif days_until_end == 3:
            subject = "Последнее напоминание: аренда заканчивается через 3 дня"
            message = f"""
            Уважаемый клиент!

            Срок аренды вашего бокса заканчивается через 3 дня ({order.end_date.strftime('%d.%m.%Y')}).

            Детали заказа:
            • Номер заказа: {order.id}
            • Объем: {order.volume}
            • Дата окончания: {order.end_date.strftime('%d.%m.%Y')}

            Не забудьте продлить аренду, чтобы продолжить пользоваться услугами хранения.

            С уважением,
            Команда selfStorage
            """
            if send_email_notification(user_email, subject, message):
                notifications_sent.append((user.id, "3_days"))

    return notifications_sent


def check_and_send_expired_notifications(db: Session) -> List[Tuple[int, str]]:
    today = datetime.date.today()
    notifications_sent = []

    expired_orders = db.query(Order).filter(
        Order.end_date.isnot(None),
        Order.end_date <= today,
        Order.end_date >= today - datetime.timedelta(days=1)
    ).all()

    for order in expired_orders:
        user = db.query(User).filter(User.id == order.user_id).first()
        if not user:
            continue

        days_after_end = (today - order.end_date).days
        user_email = get_user_email(user)

        if days_after_end == 0:
            subject = "Срок аренды истек"
            message = f"""
            Уважаемый клиент!

            Срок аренды вашего бокса истек сегодня ({order.end_date.strftime('%d.%m.%Y')}).

            Детали заказа:
            • Номер заказа: {order.id}
            • Объем: {order.volume}

            Вы можете продлить аренду за дополнительную плату.
            Стоимость продления: {order.final_price or order.estimated_price} руб. в месяц.

            Для продления свяжитесь с нами или оформите продление в личном кабинете.

            С уважением,
            Команда selfStorage
            """
            if send_email_notification(user_email, subject, message):
                notifications_sent.append((user.id, "expired_today"))

        elif days_after_end == 1:
            subject = "Ваш бокс ожидает продления"
            message = f"""
            Уважаемый клиент!

            Срок аренды вашего бокса истек вчера ({order.end_date.strftime('%d.%m.%Y')}).

            Детали заказа:
            • Номер заказа: {order.id}
            • Объем: {order.volume}

            Вы все еще можете продлить аренду за дополнительную плату.
            Стоимость продления: {order.final_price or order.estimated_price} руб. в месяц.

            Если вы не планируете продлевать аренду, пожалуйста, освободите бокс в ближайшее время.

            Для продления свяжитесь с нами.

            С уважением,
            Команда сервиса хранения
            """
            if send_email_notification(user_email, subject, message):
                notifications_sent.append((user.id, "expired_yesterday"))

    return notifications_sent
