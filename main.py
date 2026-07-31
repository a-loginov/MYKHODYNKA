from flask import Flask
from config import load_dotenv
import os

from sqlalchemy import text
from db_settings import db, bcrypt, login_manager, people
from blueprints.auth import auth
from blueprints.portal import portal


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


def _sync_schema():
    """Идемпотентно добавляет недостающие колонки и создаёт недостающие таблицы."""
    with app.app_context():
        try:
            db.session.execute(text(
                "ALTER TABLE people ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128)"
            ))
            db.session.execute(text(
                "ALTER TABLE people ADD COLUMN IF NOT EXISTS apartment VARCHAR(10)"
            ))
            db.session.execute(text(
                "ALTER TABLE people ALTER COLUMN group_number DROP NOT NULL"
            ))
            db.session.execute(text(
                "ALTER TABLE people ALTER COLUMN group_letter DROP NOT NULL"
            ))
            db.session.commit()
            # Создаём недостающие таблицы (не трогает существующие)
            db.create_all()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            print(f"[warn] schema sync skipped: {exc}")


_sync_schema()


if __name__ == "__main__":
    app.run(debug=True, port=5533, host="0.0.0.0")
