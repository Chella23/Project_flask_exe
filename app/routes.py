import datetime
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
from app.utils.task_schedular import add_scheduled_task
from . import db, mail
from .constants import Constants, Methods
from bcrypt import hashpw, gensalt, checkpw
import random
import time
from .models import db, User, DefaultCategory, DefaultWebsite, CustomCategory, CustomWebsite, Favorite,  PasswordProtection, ScheduledTask
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
# -------------------------
# Block/Unblock Website Updates
# -------------------------

@auth_bp.route('/block', methods=[Methods.POST])
def block_site():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    user_id = session["user_id"]
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request format"}), 400

    password = data.get("password")
    website_urls = data.get("websites") or []  # Expecting a list of URLs

    if isinstance(website_urls, str):  
        website_urls = [website_urls.strip()]  # Convert single string to list

    user_password_entry = PasswordProtection.query.filter_by(user_id=user_id).first()

    if user_password_entry and user_password_entry.enabled:
        if not password or not checkpw(password.encode("utf-8"), user_password_entry.password.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect password"}), 400

    blocked_websites = []
    failed_websites = []

    for website_url in website_urls:
        website_url = website_url.strip()

        if not website_url or "." not in website_url:  
            failed_websites.append(website_url)  # Mark invalid URLs as failed
            continue  # Skip blocking

        success = block_website(website_url)
        if success:
            blocked_websites.append(website_url)
        else:
            failed_websites.append(website_url)

    if blocked_websites:
        return jsonify({
            "success": True,
            "message": f"Websites blocked successfully: {', '.join(blocked_websites)}",
            "failed": failed_websites
        })
    
    return jsonify({
        "success": False,
        "message": "No valid websites were blocked.",
        "failed": failed_websites
    })


@auth_bp.route('/unblock', methods=[Methods.POST])
def unblock_site():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    user_id = session["user_id"]
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request format"}), 400

    password = data.get("password")
    website_urls = data.get("websites") or []  # Expecting a list of URLs

    if isinstance(website_urls, str):  
        website_urls = [website_urls.strip()]  # Convert single string to list

    user_password_entry = PasswordProtection.query.filter_by(user_id=user_id).first()

    if user_password_entry and user_password_entry.enabled:
        if not password or not checkpw(password.encode("utf-8"), user_password_entry.password.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect password"}), 400

    unblocked_websites = []
    failed_websites = []

    for website_url in website_urls:
        website_url = website_url.strip()

        if not website_url or "." not in website_url:  
            failed_websites.append(website_url)  # Mark invalid URLs as failed
            continue  # Skip unblocking

        success = unblock_website(website_url)
        if success:
            unblocked_websites.append(website_url)
        else:
            failed_websites.append(website_url)

    if unblocked_websites:
        return jsonify({
            "success": True,
            "message": f"Websites unblocked successfully: {', '.join(unblocked_websites)}",
            "failed": failed_websites
        })
    
    return jsonify({
        "success": False,
        "message": "No valid websites were unblocked.",
        "failed": failed_websites
    })

# -------------------------
# Categories Route
# -------------------------

# --- Categories Page ---
@auth_bp.route('/categories')
def categories():
    if 'user_id' not in session:
        flash("You need to sign in first.", "error")
        return redirect(url_for('auth.signin'))
    
    user_id = session['user_id']

    # Fetch all categories
    default_categories = DefaultCategory.query.all()
    custom_categories = CustomCategory.query.filter_by(user_id=user_id).all()

    # Fetch user's favorite entries
    user_favorites = Favorite.query.filter_by(user_id=user_id).all()

    # Build a dictionary for URL-based favorites keyed by category title.
    favorite_urls = {}
    for fav in user_favorites:
        # Determine the category title using the relationship, if available.
        if fav.default_category:
            category_title = fav.default_category.title
        elif fav.custom_category:
            category_title = fav.custom_category.title
        else:
            category_title = "Uncategorized"
        
        # Only add URL-based favorites (where fav.url is set)
        if fav.url:
            if category_title not in favorite_urls:
                favorite_urls[category_title] = []
            favorite_urls[category_title].append(fav.url)

    return render_template("categories.html", 
                           default_categories=default_categories,
                           custom_categories=custom_categories,
                           favorite_urls=favorite_urls,
                           user_favorites=[fav.default_category_id or fav.custom_category_id for fav in user_favorites])

@auth_bp.route('/add_custom_category', methods=['POST'])
def add_custom_category():
    if 'user_id' not in session:
        flash("Please log in to add custom categories.", "error")
        return redirect(url_for('auth.signin'))
    
    title = request.form.get('category_title')
    websites_str = request.form.get('category_websites')

    if not title or not websites_str:
        flash("Please provide both a title and at least one website URL.", "error")
        return redirect(url_for('auth.categories'))
    
    existing_category = CustomCategory.query.filter_by(user_id=session['user_id'], title=title).first()
    if existing_category:
        flash("A category with this title already exists.", "error")
        return redirect(url_for('auth.categories'))
    
    custom_category = CustomCategory(user_id=session['user_id'], title=title)
    db.session.add(custom_category)
    db.session.flush()  # to get the new category ID

    websites_list = [url.strip() for url in websites_str.split(",") if url.strip()]
    
    for base_url in websites_list:
        website = CustomWebsite(category_id=custom_category.id, name=base_url, url=base_url)
        db.session.add(website)

    db.session.commit()
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


@auth_bp.route("/task_schedular", methods=["GET"])
def task_schedular():
    """
    GET:
      - If the user is logged in, fetch and display all scheduled tasks.
      - Render the task scheduler page (task_schedular.html) with the tasks.
    """
    if "user_id" not in session:
        flash("Please sign in to access the Task Scheduler", "error")
        return redirect(url_for("auth.signin"))

    user_id = session["user_id"]
    # Query scheduled tasks for the current user.
    tasks = ScheduledTask.query.filter_by(user_id=user_id).all()
    return render_template("task_schedular.html", tasks=tasks)


@auth_bp.route("/add_task", methods=["POST"])
def add_task():
    """
    POST:
      - Create scheduled task(s) for the logged-in user.
      - Expected JSON payload:
            {
                "website": "www.example.com",        # The website URL (for a single task)
                "task_type": "block",                # "block" or "unblock"
                "recurring": false,                  # Boolean; false for one-time tasks
                "run_date": "2025-02-10T09:30:00",     # ISO 8601 string (if one-time)
                "day_of_week": "Mon,Tue,Wed",          # For recurring tasks (optional)
                "hour": 9,                           # For recurring tasks (optional)
                "minute": 30                         # For recurring tasks (optional)
            }
      - The utility function add_scheduled_task() handles the scheduling logic.
    """
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request data"}), 400

    user_id = session["user_id"]
    website = data.get("website")
    task_type = data.get("task_type")  # expected "block" or "unblock"
    recurring = data.get("recurring", False)
    run_date_str = data.get("run_date")  # for one-time tasks (ISO 8601 format)
    day_of_week = data.get("day_of_week")  # for recurring tasks (e.g., "Mon,Tue,Wed")
    hour = data.get("hour")
    minute = data.get("minute")

    # Convert run_date string to datetime if provided
    run_date = None
    if run_date_str:
        try:
            run_date = datetime.fromisoformat(run_date_str)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid run_date format"}), 400

    try:
        # Call your utility function to add and schedule the task.
        task = add_scheduled_task(user_id, website, task_type, run_date, recurring, day_of_week, hour, minute)
    except Exception as e:
        return jsonify({"success": False, "message": f"Error scheduling task: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "message": "Task added successfully",
        "task": task.to_dict()  # assuming your ScheduledTask model has a to_dict() method
    })


@auth_bp.route("/delete_task/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """
    DELETE:
      - Delete a scheduled task by its ID if it belongs to the logged‑in user.
    """
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 403

    task = ScheduledTask.query.get(task_id)
    if not task or task.user_id != session["user_id"]:
        return jsonify({"success": False, "message": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"success": True, "message": "Task deleted successfully"})

