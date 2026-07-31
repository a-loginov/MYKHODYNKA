from flask import Flask, render_template
from config import load_dotenv
import os

from sqlalchemy import text
from db_settings import db, bcrypt, login_manager, people
from blueprints.auth import auth
from blueprints.portal import portal
from blueprints.webauthn import webauthn_bp
from blueprints.admin import admin
from blueprints.security import security


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

db.init_app(app)
bcrypt.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(people, user_id.split('-', 1)[1])


app.register_blueprint(auth)
app.register_blueprint(portal)
app.register_blueprint(webauthn_bp)
app.register_blueprint(admin)
app.register_blueprint(security)


# ───── Единая страница ошибок ─────
ERROR_PAGES = {
    400: ("🤔", "Некорректный запрос", "Похоже, в запросе что-то не так. Попробуйте ещё раз."),
    403: ("🔒", "Доступ запрещён", "У вас нет прав для просмотра этой страницы."),
    404: ("🧭", "Страница не найдена", "Возможно, ссылка устарела или введена с ошибкой."),
    500: ("🛠️", "Что-то пошло не так", "Мы уже знаем о проблеме и уже её чиним. Попробуйте позже."),
    502: ("🛠️", "Сервис недоступен", "Идут технические работы. Обновите страницу через минуту."),
    503: ("🛠️", "Сервис временно недоступен", "Идут технические работы. Обновите страницу через минуту."),
}


def _render_error(code):
    emoji, title, message = ERROR_PAGES.get(
        code, ("⚠️", "Ошибка", "Произошла непредвиденная ошибка."))
    return render_template('error.html', code=code, emoji=emoji,
                           title=title, message=message), code


for _code in ERROR_PAGES:
    app.register_error_handler(_code, lambda e, c=_code: _render_error(c))


_SCHEMA_MIGRATIONS = [
    "ALTER TABLE people ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128)",
    "ALTER TABLE people ADD COLUMN IF NOT EXISTS apartment VARCHAR(10)",
    "ALTER TABLE people ALTER COLUMN group_number DROP NOT NULL",
    "ALTER TABLE people ALTER COLUMN group_letter DROP NOT NULL",
    "ALTER TABLE guest_pass ADD COLUMN IF NOT EXISTS arrived_at TIMESTAMP",
    "ALTER TABLE people ADD COLUMN IF NOT EXISTS phone_hidden BOOLEAN DEFAULT FALSE NOT NULL",
]


def _sync_schema():
    """Создаёт недостающие таблицы и идемпотентно дополняет существующие."""
    with app.app_context():
        try:
            # Создаём таблицы по моделям (не трогает существующие)
            db.create_all()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            print(f"[warn] create_all skipped: {exc}")

        # Каждый ALTER — в своей транзакции, чтобы падение одного
        # не откатывало остальные (иначе неполная схема → 500).
        for stmt in _SCHEMA_MIGRATIONS:
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception as exc:  # noqa: BLE001
                db.session.rollback()
                print(f"[warn] schema sync skipped: {stmt!r}: {exc}")


_sync_schema()


if __name__ == "__main__":
    app.run(debug=True, port=5533, host="0.0.0.0")
