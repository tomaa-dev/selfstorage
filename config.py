import json
from pathlib import Path
from decouple import config as env


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = env("DB_PATH")

CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    DB = json.load(f)


PROHIBITED_KEYWORDS = DB["keywords"]["prohibited_keywords"]
ALLOWED_KEYWORDS = DB["keywords"]["allowed_keywords"]

PD_PDF_PATH = BASE_DIR/"data"/DB["meta"]["pd_agreement"]["pdf_file"]

BOXES = DB["tariffs"]["boxes"]
DELIVERY_SETTINGS = DB["tariffs"]["delivery"]
MANAGER_PHONE = DB["meta"]["manager_phone"]
PROMO_CODES = DB.get("promo_codes", [])


ORDER_STATUSES = {
    "CREATED": "Создан",
    "CONFIRMED": "Подтверждён",
    "IN_STORAGE": "На хранении",
    "COMPLETED": "Завершён",
    "CANCELLED": "Отменён"
}