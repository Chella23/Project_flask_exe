"""Constants Declaration module."""
import dataclasses

@dataclasses.dataclass
class Constants:
    """User's Credentials"""
    USERNAME = "username"
    PASSWORD = "password"
    
    """HTML Pages"""
    HOME_PAGE = "home.html"
    SIGNUP_PAGE = "signup.html"
    SIGNIN_PAGE = "signin.html"
    INDEX_PAGE = "index.html"
    
    """Error messages"""
    EXIST = "Username already exists!"
    ERROR = "error"
    INVALID_EMAIL_PASSWORD = "Invalid email or password!"
    PASSWORDS_MISMATCH = "Passwords do not match!"
    EMAIL_ALREADY_REGISTERED = "Email already registered!"
    SIGNOUT_SUCCESS = "You have been logged out successfully!"
    EMAIL_REQUIRED = "Email is required"
    INVALID_EXPIRED_OTP = "Invalid or expired OTP"
    OTP_VERIFIED = "OTP verified."
    OTP_SEND_FAILURE = "Failed to send OTP. Try again."
    OTP_SENT_SUCCESS = "OTP sent to your email."
    INCORRECT_EXPIRED_OTP = "Incorrect or expired OTP"
    

    

    """Responses to frontend"""
    SIGNUP_MESSAGE = "Signup successful! Please login."
    SIGNIN_SUCCESS = "Signin successful!"

    SUCCESS = "success"
    
    """Email"""
    OTP_SUBJECT = "Your OTP Code"
    OTP_BODY = """WebsiteBlocker please verify email your code is: {}"""
    EMAIL_SENDER = "chellaamap@gmail.com"
    
@dataclasses.dataclass
class Methods:
    """HTTP Methods"""
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"
