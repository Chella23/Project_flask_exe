from flask_sqlalchemy import SQLAlchemy
from . import db 


# -------------------------
# User Table (Existing)
# -------------------------
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # If desired, you can add a relationship for custom categories:
    custom_categories = db.relationship('CustomCategory', backref='user', lazy=True)

# -------------------------
# Default Categories & Websites
# -------------------------
class DefaultCategory(db.Model):
    __tablename__ = 'default_categories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    # Relationship to the websites that belong to this default category
    websites = db.relationship('DefaultWebsite', backref='category', lazy=True, cascade="all, delete-orphan")

class DefaultWebsite(db.Model):
    __tablename__ = 'default_websites'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('default_categories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    
# -------------------------
# Custom Categories & Websites
# -------------------------
class CustomCategory(db.Model):
    __tablename__ = 'custom_categories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    # Relationship to the websites that belong to this custom category
    websites = db.relationship('CustomWebsite', backref='category', lazy=True, cascade="all, delete-orphan")

class CustomWebsite(db.Model):
    __tablename__ = 'custom_websites'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('custom_categories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
