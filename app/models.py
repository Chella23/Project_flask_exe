import datetime
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from . import db  
from sqlalchemy import CheckConstraint
# -------------------------
# User Table
# -------------------------
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
   
    mfa = db.relationship('Mfa', backref='user', uselist=False, cascade="all, delete-orphan")

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



class PasswordProtection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('password_protection', uselist=False))


# -------------------------
# Favorite Categories
# -------------------------

class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    
    # The user who made the favorite.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # For category-based favorites (favoriting an entire category).
    default_category_id = db.Column(db.Integer, db.ForeignKey('default_categories.id'), nullable=True)
    custom_category_id = db.Column(db.Integer, db.ForeignKey('custom_categories.id'), nullable=True)
    
    # For individual website favorites.
    url = db.Column(db.String(255), nullable=True)
    # Optional: store the category title for display purposes (for website favorites)
    category_title = db.Column(db.String(100), nullable=True)
    # NEW: Store the website name
    website_name = db.Column(db.String(100), nullable=True)
    
    # Ensure that at least one of the "favorite markers" is provided:
    # Either a URL is set (website favorite) OR one of the category IDs is set (category favorite).
    __table_args__ = (
        CheckConstraint(
            "(url IS NOT NULL) OR (default_category_id IS NOT NULL OR custom_category_id IS NOT NULL)",
            name="favorite_must_have_category_or_url"
        ),
    )
    
    # Relationships
    user = db.relationship('User', backref=db.backref('favorites', lazy=True))
    default_category = db.relationship('DefaultCategory', backref=db.backref('favorited_by', lazy=True))
    custom_category = db.relationship('CustomCategory', backref=db.backref('favorited_by', lazy=True))
    
    def __init__(self, user_id, url=None, default_category_id=None, custom_category_id=None, category_title=None, website_name=None):
        self.user_id = user_id
        self.url = url
        self.default_category_id = default_category_id
        self.custom_category_id = custom_category_id
        self.category_title = category_title
        self.website_name = website_name
        
    def __repr__(self):
        if self.url:
            return f"<Favorite Website {self.website_name or self.url} in Category '{self.category_title}' by User {self.user_id}>"
        else:
            cat = self.default_category.title if self.default_category else (self.custom_category.title if self.custom_category else "Unknown")
            return f"<Favorite Category {cat} by User {self.user_id}>"


class ScheduledTask(db.Model):
    __tablename__ = "scheduled_tasks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    website = db.Column(db.String(255), nullable=False)  # The website URL to block/unblock
    task_type = db.Column(db.String(10), nullable=False)   # "block" or "unblock"
    run_date = db.Column(db.DateTime, nullable=True)         # For one‑time tasks
    recurring = db.Column(db.Boolean, default=False)         # For recurring tasks
    day_of_week = db.Column(db.String(50), nullable=True)      # Comma‐separated days (e.g., "Mon,Tue,Wed")
    hour = db.Column(db.Integer, nullable=True)              # Hour (0–23) for recurring tasks
    minute = db.Column(db.Integer, nullable=True)            # Minute (0–59) for recurring tasks
    active = db.Column(db.Boolean, default=True)
    job_id = db.Column(db.String(100), nullable=True)        # APScheduler job ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "website": self.website,
            "task_type": self.task_type,
            "run_date": self.run_date.isoformat() if self.run_date else None,
            "recurring": self.recurring,
            "day_of_week": self.day_of_week,
            "hour": self.hour,
            "minute": self.minute,
            "active": self.active,
            "job_id": self.job_id
        }


# -------------------------
# MFA Table
# -------------------------
class Mfa(db.Model):
    __tablename__ = 'mfa'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), unique=True, nullable=False)
    mfa_enabled = db.Column(db.Boolean, default=False)  # MFA toggle
    six_digit_pin = db.Column(db.String(6), nullable=True)  # Encrypted 6-digit PIN (to be hashed)
    otp_attempts = db.Column(db.Integer, default=0)  # Number of OTP attempts
    otp_timestamp = db.Column(db.DateTime, nullable=True)  # Last OTP sent time

    def __init__(self, user_id, mfa_enabled=False, six_digit_pin=None):
        self.user_id = user_id
        self.mfa_enabled = mfa_enabled
        self.six_digit_pin = six_digit_pin

