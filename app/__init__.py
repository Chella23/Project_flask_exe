from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

# Initialize database and mail objects
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
    app.config['MAIL_USERNAME'] = 'chellaamap@gmail.com'  # Replace with your email
    app.config['MAIL_PASSWORD'] = 'ybsw tumb ffta lvqk'  # Replace with your email password
    app.config['MAIL_DEFAULT_SENDER'] = 'chellaamap@gmail.com'

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    # Import and register Blueprints
    from .routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
