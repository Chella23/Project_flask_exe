import datetime
import bcrypt
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
from app.utils.task_schedular import add_scheduled_task, remove_scheduled_task, init_scheduler
from . import db, mail
from .constants import Constants, Methods
from bcrypt import hashpw, gensalt, checkpw
import random
import time
from .models import Mfa, User, DefaultCategory, DefaultWebsite, CustomCategory, CustomWebsite, Favorite,  PasswordProtection, ScheduledTask, SessionToken
from sqlalchemy.orm import joinedload
from dateutil import parser
import uuid
from hashlib import sha256  # Alternative if checkpw/hashpw isn't from bcrypt
from datetime import datetime, timedelta



auth_bp = Blueprint("auth", __name__)
@auth_bp.route("/")
def index():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user:
            session.permanent = True  # Set session lifetime to 24 hours
            return redirect(url_for("auth.success"))
    return render_template(Constants.INDEX_PAGE)

@auth_bp.route("/home")
def home():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user:
            session.permanent = True
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
        session.permanent = True  # Set session lifetime to 24 hours

        # Generate and store a session token
        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=24)
        session_token = SessionToken(token=token, user_id=user.id, expires_at=expires_at)  # Fix: user.id, not user['id']
        db.session.add(session_token)
        db.session.commit()

        flash(Constants.SIGNIN_SUCCESS, "success")
        # Pass token to success template for localStorage
        return render_template(Constants.HOME_PAGE, name=user.name, session_token=token)

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

        # Use bcrypt’s hashpw (assumed from your original code)
        hashed_password = hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
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

@auth_bp.route("/verify", methods=[Methods.GET])
def verify():
    token = request.headers.get('X-Session-Token')
    if token:
        session_token = SessionToken.query.filter_by(token=token).first()
        if session_token and session_token.expires_at > datetime.utcnow():
            session['user_id'] = session_token.user_id
            session['user_name'] = User.query.get(session_token.user_id).name
            session.permanent = True
            return {"status": "verified", "user_id": session_token.user_id}
    return {"status": "not_verified"}, 401

@auth_bp.route("/signout")
def signout():
    if "user_id" in session:
        # Invalidate session token if it exists
        token = SessionToken.query.filter_by(user_id=session["user_id"]).order_by(SessionToken.expires_at.desc()).first()
        if token:
            db.session.delete(token)
            db.session.commit()
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

# ... (other routes like signin, signup, etc.)

@auth_bp.route('/block', methods=['POST'])
def block_site():
    """Blocks websites with MFA and password protection."""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    user_id = session["user_id"]
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    data = request.get_json()
    password = data.get("password")
    otp = data.get("otp")
    website_urls = data.get("websites") or []

    if isinstance(website_urls, str):
        website_urls = [website_urls.strip()]

    # Validate password if protection is enabled
    user_password_entry = PasswordProtection.query.filter_by(user_id=user_id).first()
    if user_password_entry and user_password_entry.enabled:
        if not password or not checkpw(password.encode("utf-8"), user_password_entry.password.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect password"}), 400

    blocked_websites = []
    failed_websites = []

    for website_url in website_urls:
        website_url = website_url.strip()
        if not website_url or "." not in website_url:
            failed_websites.append(website_url)
            continue
        # Call the helper function to block the website.
        success = block_website(website_url)
        if success:
            blocked_websites.append(website_url)
        else:
            failed_websites.append(website_url)

    return jsonify({
        "success": True if blocked_websites else False,
        "message": f"Websites blocked: {', '.join(blocked_websites)}" if blocked_websites else "No valid websites blocked.",
        "failed": failed_websites
    })


@auth_bp.route('/unblock', methods=['POST'])
def unblock_site():
    """Unblocks websites with MFA and password protection."""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    user_id = session["user_id"]
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    data = request.get_json()
    password = data.get("password")
    otp = data.get("otp")
    website_urls = data.get("websites") or []

    if isinstance(website_urls, str):
        website_urls = [website_urls.strip()]

    # Validate password if protection is enabled
    user_password_entry = PasswordProtection.query.filter_by(user_id=user_id).first()
    if user_password_entry and user_password_entry.enabled:
        if not password or not checkpw(password.encode("utf-8"), user_password_entry.password.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect password"}), 400

    unblocked_websites = []
    failed_websites = []

    for website_url in website_urls:
        website_url = website_url.strip()
        if not website_url or "." not in website_url:
            failed_websites.append(website_url)
            continue
        success = unblock_website(website_url)
        if success:
            unblocked_websites.append(website_url)
        else:
            failed_websites.append(website_url)

    return jsonify({
        "success": True if unblocked_websites else False,
        "message": f"Websites unblocked: {', '.join(unblocked_websites)}" if unblocked_websites else "No valid websites unblocked.",
        "failed": failed_websites
    })


@auth_bp.route("/blocked_websites", methods=["GET"])
def get_blocked_websites():
    from app.models import WebsiteHistory, db
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    user_id = session["user_id"]
    histories = WebsiteHistory.query.filter_by(user_id=user_id).order_by(WebsiteHistory.timestamp.desc()).all()
    history_list = []
    for h in histories:
        history_list.append({
            "id": h.id,
            "website": h.website,
            "action": h.action,
            "timestamp": h.timestamp.isoformat()
        })
    return jsonify({"success": True, "tasks": history_list})

# -------------------------
# Categories Route
# -------------------------
@auth_bp.route('/categories')
def categories():
    if 'user_id' not in session:
        flash("You need to sign in first.", "error")
        return redirect(url_for('auth.signin'))
    
    user_id = session['user_id']

    # Fetch default categories
    default_categories = DefaultCategory.query.all()

    # Fetch user's custom categories, ensuring relationships are loaded
    custom_categories = CustomCategory.query.filter_by(user_id=user_id).options(db.joinedload(CustomCategory.websites)).all()

    # Fetch user's favorite entries
    user_favorites = Favorite.query.filter_by(user_id=user_id).all()

    # Build a dictionary for URL-based favorites keyed by category title.
    favorite_urls = {}
    for fav in user_favorites:
        if fav.default_category:
            category_title = fav.default_category.title
        elif fav.custom_category:
            category_title = fav.custom_category.title
        else:
            category_title = "Uncategorized"
        
        if fav.url:
            if category_title not in favorite_urls:
                favorite_urls[category_title] = []
            favorite_urls[category_title].append(fav.url)

    return render_template("categories.html", 
                           default_categories=default_categories,
                           user_custom_categories=custom_categories,  # ✅ Correct variable name
                           category_icons=category_icons, 
                           website_icons=website_icons,
                           favorite_urls=favorite_urls,
                           user_favorites=[fav.default_category_id or fav.custom_category_id for fav in user_favorites])

# --- Add Custom Category ---
@auth_bp.route('/add_custom_category', methods=['POST'])
def add_custom_category():
    if 'user_id' not in session:
        flash("Please log in to add custom categories.", "error")
        return redirect(url_for('auth.signin'))
    
    user_id = session['user_id']
    title = request.form.get('category_title')
    websites_str = request.form.get('category_websites')

    if not title or not websites_str:
        flash("Please provide both a title and at least one website URL.", "error")
        return redirect(url_for('auth.categories'))
    
    # Check if the category already exists for the user
    existing_category = CustomCategory.query.filter_by(user_id=user_id, title=title).first()
    if existing_category:
        flash("A category with this title already exists.", "error")
        return redirect(url_for('auth.categories'))
    
    # Create a new custom category
    custom_category = CustomCategory(user_id=user_id, title=title)
    db.session.add(custom_category)
    db.session.flush()  # Flush to get the new category ID

    # Split websites input into a list and store them
    websites_list = [url.strip() for url in websites_str.split(",") if url.strip()]
    for base_url in websites_list:
        website = CustomWebsite(category_id=custom_category.id, name=base_url, url=base_url)
        db.session.add(website)

    db.session.commit()  # Commit changes to DB

    flash("Custom category added successfully!", "success")
    return redirect(url_for('auth.categories'))

@auth_bp.route('/add_url_to_favorites/<int:category_id>/<string:category_type>', methods=['POST'])
def add_url_to_favorites(category_id, category_type):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"})
    
    user_id = session['user_id']
    data = request.get_json()
    url = data.get('url')
    website_name = data.get('website_name')  # Expect the client to send this (optional)
    
    if not url:
        return jsonify({"success": False, "message": "No URL provided"})
    
    # Check if the URL is already favorited for this user
    existing = Favorite.query.filter_by(user_id=user_id, url=url).first()
    if existing:
        return jsonify({"success": False, "message": "URL already in favorites"})
    
    # Retrieve the category to obtain its title
    category_title = None
    if category_type == "default":
        category = DefaultCategory.query.get(category_id)
    else:
        category = CustomCategory.query.get(category_id)
    
    if category:
        category_title = category.title

    new_fav = Favorite(
        user_id=user_id,
        url=url,
        website_name=website_name,
        category_title=category_title,
        default_category_id=category_id if category_type == "default" else None,
        custom_category_id=category_id if category_type == "custom" else None
    )
    db.session.add(new_fav)
    db.session.commit()
    return jsonify({"success": True, "message": "URL added to favorites successfully"})

@auth_bp.route('/add_to_favorites/<int:category_id>/', defaults={'category_type': 'default'}, methods=['POST'])
@auth_bp.route('/add_to_favorites/<int:category_id>/<string:category_type>', methods=['POST'])
def toggle_category_favorite(category_id, category_type):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"})
    
    user_id = session['user_id']
    
    if category_type == "default":
        fav = Favorite.query.filter_by(user_id=user_id, default_category_id=category_id).first()
    else:
        fav = Favorite.query.filter_by(user_id=user_id, custom_category_id=category_id).first()
    
    if fav:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({"success": True, "message": "Removed from favorites"})
    
    # Add new favorite for the whole category (without a URL)
    if category_type == "default":
        new_fav = Favorite(user_id=user_id, default_category_id=category_id)
    else:
        new_fav = Favorite(user_id=user_id, custom_category_id=category_id)
    
    db.session.add(new_fav)
    db.session.commit()
    return jsonify({"success": True, "message": "Added to favorites"})


# -------------------------
# Favorite Categories Route
# -------------------------
@auth_bp.route('/favourites')
def favourites():
    if 'user_id' not in session:
        flash("Please log in to view favorites.", "error")
        return redirect(url_for("auth.signin"))
    
    user_id = session['user_id']
    user_favorites = Favorite.query.filter_by(user_id=user_id).all()
    
    # Build a dictionary for website-level favorites keyed by category title.
    favorite_websites = {}
    for fav in user_favorites:
        if fav.url:  # This is an individual website favorite
            if fav.default_category:
                cat_title = fav.default_category.title
            elif fav.custom_category:
                cat_title = fav.custom_category.title
            else:
                cat_title = "Uncategorized"
            if cat_title not in favorite_websites:
                favorite_websites[cat_title] = []
            favorite_websites[cat_title].append(fav.url)
            # Here, for simplicity, we use the URL as the indicator.
            # If you want to include website name and mark as favorited, you can build a dictionary:
            # favorite_websites[cat_title].append({
            #    "url": fav.url,
            #    "website_name": fav.website_name,
            #    "category_id": fav.default_category.id if fav.default_category else fav.custom_category.id,
            #    "favorited": True
            # })
    
    # Build lists for category-level favorites
    favorite_default_categories = []
    favorite_custom_categories = []
    for fav in user_favorites:
        if not fav.url:  # Category favorite (entire category)
            if fav.default_category and fav.default_category not in favorite_default_categories:
                favorite_default_categories.append(fav.default_category)
            elif fav.custom_category and fav.custom_category not in favorite_custom_categories:
                favorite_custom_categories.append(fav.custom_category)
    
    # user_favorites (used for header icon check) as a list of category IDs
    user_fav_ids = [fav.default_category_id or fav.custom_category_id for fav in user_favorites if not fav.url]

    return render_template("fav.html",
                           favorite_default_categories=favorite_default_categories,
                           favorite_custom_categories=favorite_custom_categories,
                           favorite_websites=favorite_websites,
                           category_icons=category_icons, 
                           website_icons=website_icons, 
                           user_favorites=user_fav_ids)

@auth_bp.route('/toggle_website_favorite/<int:category_id>/', defaults={'category_type': 'default'}, methods=['POST'])
@auth_bp.route('/toggle_website_favorite/<int:category_id>/<string:category_type>', methods=['POST'])
def toggle_website_favorite(category_id, category_type):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"})
    
    user_id = session['user_id']
    data = request.get_json()
    website_url = data.get('url')
    if not website_url:
        return jsonify({"success": False, "message": "No URL provided"})

    # Query for an existing website favorite for this category
    fav = Favorite.query.filter_by(user_id=user_id, url=website_url).first()
    if fav:
        # Remove this website favorite
        db.session.delete(fav)
        db.session.commit()
        return jsonify({"success": True, "message": "Website removed from favorites"})
    
    # If not already favorited, add it
    # Retrieve the category title from the respective category.
    category_title = None
    if category_type == "default":
        category = DefaultCategory.query.get(category_id)
    else:
        category = CustomCategory.query.get(category_id)
    if category:
        category_title = category.title

    new_fav = Favorite(
        user_id=user_id,
        url=website_url,
        category_title=category_title,
        default_category_id=category_id if category_type=="default" else None,
        custom_category_id=category_id if category_type=="custom" else None
    )
    db.session.add(new_fav)
    db.session.commit()
    return jsonify({"success": True, "message": "Website added to favorites"})



# -------------------------
# Password Protection Routes
# -------------------------

@auth_bp.route("/set_password", methods=["POST"])
def set_password():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403
    user_id = session["user_id"]
    data = request.json
    password = data.get("password")
    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400
    hashed_password = hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")
    existing_entry = PasswordProtection.query.filter_by(user_id=user_id).first()
    if existing_entry:
        existing_entry.password = hashed_password
    else:
        new_entry = PasswordProtection(user_id=user_id, password=hashed_password, enabled=False)
        db.session.add(new_entry)
    db.session.commit()
    return jsonify({"success": True, "message": "Password set successfully"})

@auth_bp.route("/enable_protection", methods=["POST"])
def enable_protection():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403
    user_id = session["user_id"]
    entry = PasswordProtection.query.filter_by(user_id=user_id).first()
    if not entry:
        return jsonify({"success": False, "message": "Set a password first"}), 400
    entry.enabled = True
    db.session.commit()
    return jsonify({"success": True})

@auth_bp.route("/disable_protection", methods=["POST"])
def disable_protection():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403
    user_id = session["user_id"]
    data = request.json
    password = data.get("password")
    entry = PasswordProtection.query.filter_by(user_id=user_id).first()
    if not entry or not checkpw(password.encode("utf-8"), entry.password.encode("utf-8")):
        return jsonify({"success": False, "message": "Incorrect password"}), 400
    # Delete the stored password to disable protection entirely.
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"success": True})

@auth_bp.route("/get_protection_status", methods=["GET"])
def get_protection_status():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 403
    password_entry = PasswordProtection.query.filter_by(user_id=user_id).first()
    is_password_set = password_entry is not None and password_entry.password is not None
    return jsonify({
        "enabled": password_entry.enabled if password_entry else False,
        "password_set": is_password_set
    })

@auth_bp.route("/password_protection", methods=["GET"])
def password_protection():
    """
    Serves the Password Protection setup page.
    """
    return render_template("pass_pro.html")


# -------------------------
# Get Scheduled Tasks
# -------------------------
@auth_bp.route("/get_tasks", methods=["GET"])
def get_tasks():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403
    user_id = session["user_id"]
    tasks = ScheduledTask.query.filter_by(user_id=user_id, active=True).all()
    tasks_list = [task.to_dict() for task in tasks]  # Make sure ScheduledTask has a to_dict() method.
    return jsonify({"success": True, "tasks": tasks_list})

# -------------------------
# Task Scheduler Routes
# -------------------------
@auth_bp.route("/task_schedular", methods=["GET"])
def task_schedular():
    if "user_id" not in session:
        flash("Please sign in to access the Task Scheduler", "error")
        return redirect(url_for("auth.signin"))
    user_id = session["user_id"]
    tasks = ScheduledTask.query.filter_by(user_id=user_id, active=True).all()
    return render_template("task_schedular.html", tasks=tasks)

@auth_bp.route("/add_task", methods=["POST"])
def add_task():
    """
    Expects a JSON payload with the following keys:

    Common:
      - "website": A multiline string containing one or more website URLs (one per line).
      - "recurring": Boolean; true for recurring tasks.
      
    For one-time tasks:
      - "block_time": ISO datetime string for the block (start) time (e.g. "2025-02-10T09:30" or "2025-02-10T09:30:00").
      - "unblock_time": ISO datetime string for the unblock (end) time.
      
    For recurring tasks:
      - "day_of_week": Comma-separated string of days (e.g. "mon,tue,wed").
      - "block_time": Time string in HH:MM format for block.
      - "unblock_time": Time string in HH:MM format for unblock.
      
    For each valid website (each nonempty line that contains a dot), two tasks are created:
      one scheduled to block at the specified start time and one scheduled to unblock at the specified end time.
    """
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request data"}), 400

    user_id = session["user_id"]
    websites_text = data.get("website")
    recurring = data.get("recurring", False)

    if not websites_text:
        return jsonify({"success": False, "message": "No website(s) provided"}), 400

    # Split by newline and only keep lines that contain a dot (very basic validation)
    websites = [line.strip() for line in websites_text.split("\n") if line.strip() and "." in line.strip()]
    if not websites:
        return jsonify({"success": False, "message": "No valid website URLs found."}), 400

    tasks_created = []
    if recurring:
        day_of_week = data.get("day_of_week")  # e.g. "mon,tue,wed"
        block_time_str = data.get("block_time")  # e.g. "09:30"
        unblock_time_str = data.get("unblock_time")  # e.g. "17:00"
        if not day_of_week or not block_time_str or not unblock_time_str:
            return jsonify({"success": False, "message": "Recurring tasks require day_of_week, block_time, and unblock_time"}), 400
        try:
            block_hour, block_minute = map(int, block_time_str.split(":"))
            unblock_hour, unblock_minute = map(int, unblock_time_str.split(":"))
        except Exception as e:
            return jsonify({"success": False, "message": "Invalid time format. Use HH:MM."}), 400

        for website in websites:
            block_task = add_scheduled_task(
                user_id, website, task_type="block",
                recurring=True, day_of_week=day_of_week,
                block_hour=block_hour, block_minute=block_minute
            )
            unblock_task = add_scheduled_task(
                user_id, website, task_type="unblock",
                recurring=True, day_of_week=day_of_week,
                unblock_hour=unblock_hour, unblock_minute=unblock_minute
            )
            tasks_created.extend([block_task.to_dict(), unblock_task.to_dict()])
    else:
        block_time_str = data.get("block_time")  # e.g. "2025-02-10T09:30" or with seconds "2025-02-10T09:30:00"
        unblock_time_str = data.get("unblock_time")
        if not block_time_str or not unblock_time_str:
            return jsonify({"success": False, "message": "One-time tasks require both block_time and unblock_time"}), 400

        # Append seconds if missing (length 16 indicates format "YYYY-MM-DDTHH:MM")

        try:
            run_date_block = parser.parse(block_time_str)
            run_date_unblock = parser.parse(unblock_time_str)
        except Exception as e:
            return jsonify({"success": False, "message": "Invalid datetime format"}), 400


        for website in websites:
            block_task = add_scheduled_task(
                user_id, website, task_type="block",
                run_date=run_date_block, recurring=False
            )
            unblock_task = add_scheduled_task(
                user_id, website, task_type="unblock",
                run_date=run_date_unblock, recurring=False
            )
            tasks_created.extend([block_task.to_dict(), unblock_task.to_dict()])

    if tasks_created:
        return jsonify({"success": True, "message": "Tasks scheduled successfully", "tasks": tasks_created})
    else:
        return jsonify({"success": False, "message": "Error scheduling tasks"}), 500

@auth_bp.route("/delete_task/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403
    task = ScheduledTask.query.get(task_id)
    if not task or task.user_id != session["user_id"]:
        return jsonify({"success": False, "message": "Task not found"}), 404
    if remove_scheduled_task(task_id):
        return jsonify({"success": True, "message": "Task deleted successfully"})
    else:
        return jsonify({"success": False, "message": "Error deleting task"}), 500


@auth_bp.route("/get_mfa_status", methods=["GET"])
def get_mfa_status():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    mfa = Mfa.query.filter_by(user_id=user_id).first()
    # Return true only if an MFA record exists and is enabled.
    return jsonify({"mfa_enabled": bool(mfa and mfa.mfa_enabled)})


@auth_bp.route("/toggle_mfa", methods=["POST"])
def toggle_mfa():
    """
    This endpoint is used for enabling MFA once the user has completed OTP verification
    and provided a valid six-digit PIN.
    """
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.get_json()
    enable_mfa = data.get("enable")

    # Fetch any existing MFA record
    mfa = Mfa.query.filter_by(user_id=user_id).first()

    if enable_mfa:
        # When enabling, we expect a valid 6-digit PIN (OTP is already verified in a separate flow)
        six_digit_pin = data.get("six_digit_pin")
        if not six_digit_pin or not six_digit_pin.isdigit() or len(six_digit_pin) != 6:
            return jsonify({"error": "Invalid PIN. Must be a 6-digit number."}), 400

        hashed_pin = bcrypt.hashpw(six_digit_pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        if not mfa:
            mfa = Mfa(user_id=user_id, mfa_enabled=True, six_digit_pin=hashed_pin)
            db.session.add(mfa)
        else:
            mfa.mfa_enabled = True
            mfa.six_digit_pin = hashed_pin

        db.session.commit()
        return jsonify({"success": True, "message": "MFA enabled successfully"})

    else:
        # When disabling MFA, remove the record (after OTP & PIN verification on the frontend)
        if mfa:
            db.session.delete(mfa)
            db.session.commit()
            return jsonify({"success": True, "message": "MFA disabled successfully"})
        else:
            return jsonify({"error": "MFA is not enabled"}), 400

@auth_bp.route("/verify_mfa", methods=["POST"])
def verify_mfa():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    otp = data.get("otp")
    six_digit_pin = data.get("six_digit_pin")

    user_id = session["user_id"]
    mfa = Mfa.query.filter_by(user_id=user_id).first()

    if "otp" not in session or "otp_expiry" not in session:
        return jsonify({"error": "OTP expired or not found. Please request a new one."}), 400

    if time.time() > session.get("otp_expiry"):
        session.pop("otp", None)
        session.pop("otp_expiry", None)
        return jsonify({"error": "OTP expired. Please request a new one."}), 400

    try:
        entered_otp = int(otp)
    except ValueError:
        return jsonify({"error": "Invalid OTP format. OTP should be a 6-digit number."}), 400

    if entered_otp != session.get("otp"):
        return jsonify({"error": "Invalid OTP"}), 400

    session.pop("otp", None)
    session.pop("otp_expiry", None)

    if not mfa:
        return jsonify({"success": True, "message": "OTP verified. Please set your 6-digit PIN."})

    # If user is disabling MFA, return a special message to trigger PIN input in the frontend.
    return jsonify({"success": True, "message": "OTP verified. Please enter your 6-digit PIN to disable MFA.", "require_pin": True})


@auth_bp.route("/set_pin", methods=["POST"])
def set_pin():
    """
    This endpoint is used when the user sets their six-digit PIN during MFA setup.
    It creates or updates the MFA record with the provided PIN.
    """
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    pin = data.get("pin")

    if not pin or len(pin) != 6 or not pin.isdigit():
        return jsonify({"error": "PIN must be a 6-digit number"}), 400

    hashed_pin = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = session["user_id"]
    mfa = Mfa.query.filter_by(user_id=user_id).first()

    if mfa:
        mfa.six_digit_pin = hashed_pin
        mfa.mfa_enabled = True
    else:
        mfa = Mfa(user_id=user_id, mfa_enabled=True, six_digit_pin=hashed_pin)
        db.session.add(mfa)

    db.session.commit()
    return jsonify({"success": True, "message": "MFA enabled successfully!"})

@auth_bp.route("/disable_mfa", methods=["POST"])
def disable_mfa():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    pin = data.get("pin")  # Get the PIN from frontend

    user_id = session["user_id"]
    mfa = Mfa.query.filter_by(user_id=user_id).first()

    if not mfa or not mfa.six_digit_pin:  # Check if MFA is not set or PIN is missing
        return jsonify({"error": "MFA is not enabled or PIN is missing"}), 400

    # Verify the entered PIN against the stored hashed PIN
    stored_hashed = mfa.six_digit_pin.encode('utf-8')

    try:
        if not bcrypt.checkpw(pin.encode("utf-8"), stored_hashed):
            return jsonify({"error": "Incorrect 6-digit PIN"}), 400  # Reject incorrect PIN
    except ValueError:  # Handle invalid hash (if data is corrupted)
        return jsonify({"error": "Invalid stored PIN. Please reset MFA."}), 500

    db.session.delete(mfa)
    db.session.commit()

    return jsonify({"success": True, "message": "MFA disabled successfully"})



@auth_bp.route("/get_user_email", methods=["GET"])
def get_user_email():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session["user_id"])
    if user:
        return jsonify({"email": user.email})
    return jsonify({"error": "User not found"}), 404


@auth_bp.route("/MFA", methods=["GET"])
def MFA():
    return render_template("mfa.html")



# In your Flask route or seeds.py
category_icons = {
    "Social Media": "bi bi-people-fill",
    "Streaming": "bi bi-play-btn-fill",
    "Shopping": "bi bi-cart-fill",
    "News": "bi bi-newspaper",
    "Gaming": "bi bi-controller",
    "Education": "bi bi-book-fill",
    "AI Tools": "bi bi-robot",
    "Finance": "bi bi-currency-dollar",
    "Health": "bi bi-heart-fill",
    "Productivity": "bi bi-check2-square"
}

website_icons = {
    "facebook.com": "bi bi-facebook",
    "twitter.com": "bi bi-twitter",
    "instagram.com": "bi bi-instagram",
    "snapchat.com": "bi bi-camera-fill",
    "tiktok.com": "bi bi-music-note",
    "reddit.com": "bi bi-chat-left-text-fill",
    "linkedin.com": "bi bi-linkedin",
    "pinterest.com": "bi bi-pin-angle-fill",
    "quora.com": "bi bi-question-circle-fill",
    "tumblr.com": "bi bi-images",
    "youtube.com": "bi bi-youtube",
    "netflix.com": "bi bi-play-circle-fill",
    "hulu.com": "bi bi-play-btn",
    "disneyplus.com": "bi bi-magic",
    "primevideo.com": "bi bi-play-circle",
    "hbomax.com": "bi bi-tv-fill",
    "twitch.tv": "bi bi-camera-video-fill",
    "crunchyroll.com": "bi bi-play-btn",
    "hbo.com": "bi bi-tv-fill",
    "vimeo.com": "bi bi-play-circle",
    "amazon.com": "bi bi-box-seam-fill",
    "ebay.com": "bi bi-cart-check-fill",
    "walmart.com": "bi bi-cart-fill",
    "aliexpress.com": "bi bi-cart-plus-fill",
    "etsy.com": "bi bi-gift-fill",
    "target.com": "bi bi-cart-fill",
    "flipkart.com": "bi bi-cart-fill",
    "bestbuy.com": "bi bi-cart-fill",
    "zara.com": "bi bi-bag-fill",
    "ikea.com": "bi bi-house-fill",
    "cnn.com": "bi bi-newspaper",
    "bbc.com": "bi bi-newspaper",
    "nytimes.com": "bi bi-newspaper",
    "foxnews.com": "bi bi-newspaper",
    "theguardian.com": "bi bi-newspaper",
    "washingtonpost.com": "bi bi-newspaper",
    "reuters.com": "bi bi-newspaper",
    "bloomberg.com": "bi bi-graph-up",
    "forbes.com": "bi bi-graph-up",
    "time.com": "bi bi-clock-fill",
    "steampowered.com": "bi bi-controller",
    "epicgames.com": "bi bi-controller",
    "roblox.com": "bi bi-joystick",
    "minecraft.net": "bi bi-cube-fill",
    "playstation.com": "bi bi-controller",
    "xbox.com": "bi bi-controller",
    "nintendo.com": "bi bi-controller",
    "rockstargames.com": "bi bi-controller",
    "ea.com": "bi bi-controller",
    "khanacademy.org": "bi bi-book-fill",
    "coursera.org": "bi bi-book-fill",
    "udemy.com": "bi bi-book-fill",
    "edx.org": "bi bi-book-fill",
    "academia.edu": "bi bi-file-earmark-text-fill",
    "duolingo.com": "bi bi-chat-left-text-fill",
    "mit.edu": "bi bi-book-fill",
    "stanford.edu": "bi bi-book-fill",
    "harvard.edu": "bi bi-book-fill",
    "codecademy.com": "bi bi-code-slash",
    "chat.openai.com": "bi bi-robot",
    "bard.google.com": "bi bi-robot",
    "huggingface.co": "bi bi-robot",
    "runwayml.com": "bi bi-robot",
    "midjourney.com": "bi bi-robot",
    "notion.so/ai": "bi bi-robot",
    "github.com/copilot": "bi bi-code-slash",
    "deeplearning.ai": "bi bi-robot",
    "elevenlabs.io": "bi bi-music-note",
    "stability.ai": "bi bi-robot",
    "paypal.com": "bi bi-currency-dollar",
    "stripe.com": "bi bi-credit-card-fill",
    "bankofamerica.com": "bi bi-bank",
    "wellsfargo.com": "bi bi-bank",
    "chase.com": "bi bi-bank",
    "hsbc.com": "bi bi-bank",
    "goldmansachs.com": "bi bi-graph-up",
    "nasdaq.com": "bi bi-graph-up",
    "webmd.com": "bi bi-heart-fill",
    "mayoclinic.org": "bi bi-heart-fill",
    "healthline.com": "bi bi-heart-fill",
    "nih.gov": "bi bi-heart-fill",
    "who.int": "bi bi-heart-fill",
    "clevelandclinic.org": "bi bi-heart-fill",
    "cdc.gov": "bi bi-heart-fill",
    "medscape.com": "bi bi-heart-fill",
    "medlineplus.gov": "bi bi-heart-fill",
    "drugs.com": "bi bi-capsule-fill",
    "notion.so": "bi bi-check2-square",
    "trello.com": "bi bi-check2-square",
    "asana.com": "bi bi-check2-square",
    "monday.com": "bi bi-check2-square",
    "slack.com": "bi bi-chat-left-text-fill",
    "zoom.us": "bi bi-camera-video-fill",
    "evernote.com": "bi bi-file-earmark-text-fill",
    "googlekeep.com": "bi bi-sticky-fill",
    "todoist.com": "bi bi-check2-square",
    "clickup.com": "bi bi-check2-square"
}