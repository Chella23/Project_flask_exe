from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from flask_mail import Message
from app.utils.site_blocker import block_website, unblock_website
from . import db, mail
from .constants import Constants, Methods
from bcrypt import hashpw, gensalt, checkpw
import random
import time
from .models import db, User, DefaultCategory, DefaultWebsite, CustomCategory, CustomWebsite
from sqlalchemy.orm import joinedload

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    return render_template(Constants.INDEX_PAGE)

@auth_bp.route("/home")
def home():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user:
            return redirect(url_for("auth.success"))
    return render_template(Constants.HOME_PAGE)

@auth_bp.route("/signin", methods=[Methods.GET, Methods.POST])
def signin():
    if request.method == Methods.GET:
        return render_template(Constants.SIGNIN_PAGE)

    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()

    if user and checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
        session["user_id"] = user.id
        session["user_name"] = user.name
        flash(Constants.SIGNIN_SUCCESS, "success")
        return redirect(url_for("auth.success"))

    flash(Constants.INVALID_EMAIL_PASSWORD, "error")
    return redirect(url_for("auth.signin"))

@auth_bp.route("/signup", methods=[Methods.GET, Methods.POST])
def signup():
    if request.method == Methods.POST:
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash(Constants.PASSWORDS_MISMATCH, "error")
            return redirect(url_for("auth.signup"))

        if User.query.filter_by(email=email).first():
            flash(Constants.EMAIL_ALREADY_REGISTERED, "error")
            return redirect(url_for("auth.signup"))

        hashed_password = hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash(Constants.SIGNUP_MESSAGE, "success")
        return redirect(url_for("auth.home"))

    return render_template(Constants.SIGNUP_PAGE)

@auth_bp.route("/success")
def success():
    if "user_id" in session:
        user_name = session.get("user_name", "User")
        return render_template(Constants.HOME_PAGE, name=user_name)
    return redirect(url_for("auth.signin"))

@auth_bp.route("/signout")
def signout():
    session.clear()
    flash(Constants.SIGNOUT_SUCCESS, "success")
    return redirect(url_for("auth.home"))

@auth_bp.route("/send_otp", methods=[Methods.POST])
def send_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": Constants.EMAIL_REQUIRED}), 400

    otp = random.randint(100000, 999999)
    session["otp"] = otp
    session["otp_expiry"] = time.time() + 300  # OTP expires in 5 minutes

    try:
        msg = Message(
            Constants.OTP_SUBJECT,
            sender=Constants.EMAIL_SENDER,
            recipients=[email]
        )
        msg.body = Constants.OTP_BODY.format(otp)
        mail.send(msg)
        return jsonify({"success": True, "message": Constants.OTP_SENT_SUCCESS})
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({"error": Constants.OTP_SEND_FAILURE}), 500

@auth_bp.route("/verify_otp", methods=[Methods.POST])
def verify_otp():
    data = request.get_json()
    otp = data.get("otp")

    if not otp or "otp" not in session:
        return jsonify({"error": Constants.INVALID_EXPIRED_OTP}), 400

    if int(otp) == session["otp"] and time.time() <= session["otp_expiry"]:
        session.pop("otp", None)
        session.pop("otp_expiry", None)
        return jsonify({"success": True, "message": Constants.OTP_VERIFIED})

    return jsonify({"error": Constants.INCORRECT_EXPIRED_OTP}), 400

@auth_bp.route('/block', methods=[Methods.POST])
def block_site():
    data = request.json
    website_url = data.get("website_url")

    if not website_url:
        return jsonify({"success": False, "message": "Invalid website URL"})

    success = block_website(website_url)
    return jsonify({"success": success, "action": "block", "website_url": website_url})

@auth_bp.route('/unblock', methods=[Methods.POST])
def unblock_site():
    data = request.json
    website_url = data.get("website_url")

    if not website_url:
        return jsonify({"success": False, "message": "Invalid website URL"})

    success = unblock_website(website_url)
    return jsonify({"success": success, "action": "unblock", "website_url": website_url})

@auth_bp.route('/categories')
def categories():
    user_id = session.get('user_id')

    default_categories = DefaultCategory.query.options(joinedload(DefaultCategory.websites)).all()
    user_custom_categories = []

    if user_id:
        user_custom_categories = CustomCategory.query.filter_by(user_id=user_id).options(joinedload(CustomCategory.websites)).all()

    return render_template("categories.html", 
                           default_categories=default_categories, 
                           user_custom_categories=user_custom_categories)

@auth_bp.route('/add_custom_category', methods=[Methods.POST])
def add_custom_category():
    if not session.get('user_id'):
        flash("Please log in to add custom categories.", "error")
        return redirect(url_for('auth.signin'))
    
    title = request.form.get('category_title')
    websites_str = request.form.get('category_websites')

    if not title or not websites_str:
        flash("Please provide both a title and at least one website URL.", "error")
        return redirect(url_for('auth.categories'))
    
    existing_category = CustomCategory.query.filter_by(user_id=session.get('user_id'), title=title).first()
    if existing_category:
        flash("A category with this title already exists.", "error")
        return redirect(url_for('auth.categories'))
    
    custom_category = CustomCategory(user_id=session.get('user_id'), title=title)
    db.session.add(custom_category)
    db.session.flush()

    websites_list = [url.strip() for url in websites_str.split(",") if url.strip()]
    
    for base_url in websites_list:
        website1 = CustomWebsite(category_id=custom_category.id, name=base_url, url=base_url)
        db.session.add(website1)

    db.session.commit()

    flash("Custom category added successfully!", "success")
    return redirect(url_for('auth.categories'))
