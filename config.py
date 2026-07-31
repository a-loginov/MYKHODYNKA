import os
from dotenv import load_dotenv


load_dotenv()



# Настройка базы данных   
# os.environ[...] выбросит ошибку, если переменная не найдена,
# что предотвратит запуск с неполной конфигурацией.#

DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ['DB_PORT']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_NAME = os.environ['DB_NAME']


# Flask ключ для подписывания сесеий #
SECRET_KEY = os.environ['SECRET_KEY']



# Мастер-пароль от админ панели #
MASTER_PASSWORD = os.environ["MASTER_PASSWORD"]


# Пароль для страницы охраны (если не задан — используется мастер-пароль) #
SECURITY_PASSWORD = os.environ.get("SECURITY_PASSWORD", MASTER_PASSWORD)


# WebAuthn (Face ID / Touch ID) — RP ID должен совпадать с доменом сайта
RP_ID = os.environ.get("RP_ID", "localhost")
RP_NAME = os.environ.get("RP_NAME", "MYKHODYNKA")
RP_ORIGIN = os.environ.get("RP_ORIGIN", "http://localhost:5533")
