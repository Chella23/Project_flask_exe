# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

# Create the single instances
db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Application Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/user_management'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'

    # Flask-Mail Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'chellaamap@gmail.com'
    app.config['MAIL_PASSWORD'] = 'ybsw tumb ffta lvqk'
    app.config['MAIL_DEFAULT_SENDER'] = 'chellaamap@gmail.com'

    # Initialize extensions with the app
    db.init_app(app)
    mail.init_app(app)

    # Register Blueprints
    from .routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/')

    # Create tables and seed default categories within an app context.
    with app.app_context():
        db.create_all()
        from .seeds import init_default_categories
        init_default_categories()

    return app
