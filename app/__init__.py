# app/__init__.py
import os
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from datetime import timedelta
from flask_session import Session
from dotenv import load_dotenv
import os

load_dotenv()


db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/user_management'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    Session(app)

  

    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

    db.init_app(app)
    mail.init_app(app)

    from .routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/')

    @app.before_request
    def log_session():
        print(f"Session data: {dict(session)}")

    with app.app_context():
        db.create_all()
        from .seeds import init_default_categories
        init_default_categories()
        from app.utils.task_schedular import init_scheduler
        init_scheduler(app)
        print(f"Session file directory set to: {app.config['SESSION_FILE_DIR']}")

    return app