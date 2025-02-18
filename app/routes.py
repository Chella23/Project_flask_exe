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
from .models import Mfa, db, User, DefaultCategory, DefaultWebsite, CustomCategory, CustomWebsite, Favorite,  PasswordProtection, ScheduledTask
from sqlalchemy.orm import joinedload
from dateutil import parser


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
# -------------------------
# Block/Unblock Website Updates
# -------------------------

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

    # # Validate OTP if MFA is enabled
    # if user.mfa_enabled:
    #     if not otp or not verify_otp(otp):
    #         return jsonify({"success": False, "message": "Invalid or expired OTP"}), 400
    #     session.pop("otp", None)
    #     session.pop("otp_expiry", None)

    # Validate password if password protection is enabled
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

    # # Validate OTP if MFA is enabled
    # if user.mfa_enabled:
    #     if not otp or not verify_otp(otp):
    #         return jsonify({"success": False, "message": "Invalid or expired OTP"}), 400
    #     session.pop("otp", None)
    #     session.pop("otp_expiry", None)

    # Validate password if password protection is enabled
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

    return jsonify({"mfa_enabled": bool(mfa)})  # Return True if MFA record exists
@auth_bp.route("/toggle_mfa", methods=["POST"])
def toggle_mfa():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.get_json()
    enable_mfa = data.get("enable")
    
    # Fetch existing MFA record
    mfa = Mfa.query.filter_by(user_id=user_id).first()

    if enable_mfa:
        six_digit_pin = data.get("six_digit_pin")
        # Validate PIN
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
    
    # If disabling MFA
    else:
        if mfa:
            db.session.delete(mfa)
            db.session.commit()
        return jsonify({"success": True, "message": "MFA disabled successfully"})


@auth_bp.route("/verify_mfa", methods=["POST"])
def verify_mfa():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    otp = data.get("otp")  # OTP entered by user
    six_digit_pin = data.get("six_digit_pin")  # PIN (if needed)

    user_id = session["user_id"]
    mfa = Mfa.query.filter_by(user_id=user_id).first()

    # Check if OTP exists in session
    if "otp" not in session or "otp_expiry" not in session:
        return jsonify({"error": "OTP expired or not found. Please request a new one."}), 400

    # Check OTP expiry
    otp_expiry = session.get("otp_expiry")
    if time.time() > otp_expiry:
        # Clear OTP session data after expiry
        session.pop("otp", None)
        session.pop("otp_expiry", None)
        return jsonify({"error": "OTP expired. Please request a new one."}), 400

    # Ensure OTP is entered correctly (converted to integer for comparison)
    try:
        entered_otp = int(otp)  # Convert to integer to compare
    except ValueError:
        return jsonify({"error": "Invalid OTP format. OTP should be a 6-digit number."}), 400

    # Verify the OTP
    if entered_otp != session.get("otp"):
        return jsonify({"error": "Invalid OTP"}), 400

    # Clear OTP from session after successful verification
    session.pop("otp", None)
    session.pop("otp_expiry", None)

    # If OTP is correct but MFA is not set up yet, ask for PIN setup
    if not mfa:
        return jsonify({"success": True, "message": "OTP verified. Please set your 6-digit PIN."})

    # If MFA is set, validate 6-digit PIN if provided
    if six_digit_pin:
        # Hash the entered PIN and compare it with the stored hashed PIN
        hashed_pin = mfa.six_digit_pin.encode('utf-8')  # Assuming stored pin is already hashed

        if not bcrypt.checkpw(six_digit_pin.encode("utf-8"), hashed_pin):  # Hash the entered PIN and compare
            return jsonify({"error": "Incorrect 6-digit PIN"}), 400

        return jsonify({"success": True, "message": "MFA verification successful"})

    return jsonify({"error": "Please enter your 6-digit PIN to complete the process."}), 400


    
@auth_bp.route("/get_user_email", methods=["GET"])
def get_user_email():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session["user_id"])
    if user:
        return jsonify({"email": user.email})
    return jsonify({"error": "User not found"}), 404

@auth_bp.route("/set_pin", methods=["POST"])
def set_pin():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    pin = data.get("pin")

    if not pin or len(pin) != 6 or not pin.isdigit():
        return jsonify({"error": "PIN must be a 6-digit number"}), 400

    hashed_pin = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user_id = session["user_id"]
    existing_mfa = Mfa.query.filter_by(user_id=user_id).first()

    if existing_mfa:
        existing_mfa.six_digit_pin = hashed_pin
    else:
        new_mfa = Mfa(user_id=user_id, six_digit_pin=hashed_pin)
        db.session.add(new_mfa)

    db.session.commit()

    return jsonify({"success": True, "message": "MFA enabled successfully!"})

@auth_bp.route("/disable_mfa", methods=["POST"])
def disable_mfa():
    user = User.query.get(session['user_id'])
    user.mfa_enabled = False
    user.pin = None
    db.session.commit()
    return jsonify({"success": True, "message": "MFA disabled"})



@auth_bp.route("/MFA", methods=["GET"])
def MFA():
    return render_template("mfa.html")