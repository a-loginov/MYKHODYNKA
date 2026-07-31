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
