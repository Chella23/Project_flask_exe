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
from flask_mail import Message, Mail
from app.utils.site_blocker import block_website, unblock_website
from . import db, mail
from .constants import Constants, Methods
from bcrypt import hashpw, gensalt, checkpw
import random
import time


auth_bp = Blueprint("auth", __name__)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)



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
        # Render the signin page
        return render_template(Constants.SIGNIN_PAGE)

    # Handle POST request for signin
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()

    if user and checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
        session["user_id"] = user.id
        session["user_name"] = user.name
        flash(Constants.signin_SUCCESS, Constants.SUCCESS)
        return redirect(url_for("auth.success"))

    flash(Constants.INVALID_EMAIL_PASSWORD, Constants.ERROR)
    return redirect(url_for("auth.signin"))



@auth_bp.route("/signup", methods=[Methods.GET, Methods.POST])
def signup():
    if request.method == Methods.POST:
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash(Constants.PASSWORDS_MISMATCH, Constants.ERROR)
            return redirect(url_for("auth.signup"))

        if User.query.filter_by(email=email).first():
            flash(Constants.EMAIL_ALREADY_REGISTERED, Constants.ERROR)
            return redirect(url_for("auth.signup"))

        hashed_password = hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash(Constants.SIGNUP_MESSAGE, Constants.SUCCESS)
        return redirect(url_for("auth.home"))

    return render_template(Constants.SIGNUP_PAGE)


@auth_bp.route("/success")
def success():
    if "user_id" in session:
        user_name = session.get("user_name", "User")
        return render_template(Constants.HOME_PAGE, name=user_name)
    return redirect(url_for("auth.signin"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash(Constants.LOGOUT_SUCCESS, Constants.SUCCESS)
    return redirect(url_for("auth.home"))


@auth_bp.route("/send_otp", methods=[Methods.POST])
def send_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": Constants.EMAIL_REQUIRED}), 400

    otp = random.randint(100000, 999999)
    session["otp"] = otp
    session["otp_expiry"] = time.time() + 300

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

@auth_bp.route('/block', methods=[Methods.GET, Methods.POST])
def block_site():
    data = request.json
    website_url = data.get("website_url")

    if not website_url:
        return jsonify({"success": False, "message": "Invalid website URL"})

    success = block_website(website_url)
    return jsonify({"success": success, "action": "block", "website_url": website_url})

@auth_bp.route('/unblock',methods=[Methods.GET, Methods.POST])
def unblock_site():
    data = request.json
    website_url = data.get("website_url")

    if not website_url:
        return jsonify({"success": False, "message": "Invalid website URL"})

    success = unblock_website(website_url)
    return jsonify({"success": success, "action": "unblock", "website_url": website_url})
