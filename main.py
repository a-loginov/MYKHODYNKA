from flask import Flask
from config import load_dotenv
import os

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


if __name__ == "__main__":
    app.run(debug=True, port=5533, host="0.0.0.0")
