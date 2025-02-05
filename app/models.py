from flask_sqlalchemy import SQLAlchemy
from . import db  

# -------------------------
# User Table
# -------------------------
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # Relationship to custom categories
    custom_categories = db.relationship('CustomCategory', backref='user', lazy=True, cascade="all, delete-orphan")

# -------------------------
# Default Categories & Websites
# -------------------------
class DefaultCategory(db.Model):
    __tablename__ = 'default_categories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True)

    # Relationship to websites
    websites = db.relationship('DefaultWebsite', backref='category', lazy=True, cascade="all, delete-orphan")

class DefaultWebsite(db.Model):
    __tablename__ = 'default_websites'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('default_categories.id', ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False, unique=True)

# -------------------------
# Custom Categories & Websites
# -------------------------
class CustomCategory(db.Model):
    __tablename__ = 'custom_categories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(100), nullable=False)

    # Relationship to websites
    websites = db.relationship('CustomWebsite', backref='category', lazy=True, cascade="all, delete-orphan")

class CustomWebsite(db.Model):
    __tablename__ = 'custom_websites'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('custom_categories.id', ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False, unique=True)
