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