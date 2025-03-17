import bcrypt
import random
from knowledge_base import KnowledgeBase
from email_handler import EmailHandler
from flask import flash
import logging
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import UserMixin

knowledge_base = KnowledgeBase()
email_handler = EmailHandler()

# User model for authentication
class User(UserMixin):
    """
    User model for managing login sessions with Flask-Login.
    """
    def __init__(self, id):
        self.id = id


# Login form using Flask-WTF
class LoginForm(FlaskForm):
    """
    Login form for user authentication, includes Login ID and Password fields.
    """
    loginId = StringField('Login ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class AuthHandler:

    # Authentication function
    def authenticate_user(self, email_id, password):
        """
        Authenticate the user by verifying the login ID and password.
        Uses bcrypt for password hashing and comparison.
        """
        success, result = knowledge_base.get_admin_details(email_id=email_id)
        if not success:
            flash(result, "error")
            return False, None

        if result:
            stored_password = result.get('password')
            # Verify the password with bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                return True, result
            else:
                flash("Invalid password.", "error")
        else:
            flash("User not found.", "error")

        return False, None

    def generate_and_send_reset_code(self, email_id):
        """
        Generate a 6-digit reset code, hash it, store it, and send it to the email.
        """
        # Generate a random 6-digit code
        reset_code = str(random.randint(100000, 999999))
        success, message = knowledge_base.store_password_reset_code(email_id, reset_code)
        if not success:
            return False, message

        subject = f"Password Reset Request - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        reset_email_content = (
            f"Hello,\n\n"
            f"We received a request to reset your password for your Craigslist SafeBot account. "
            f"To proceed with resetting your password, please use the following verification code:\n\n"
            f"🔑 Your Password Reset Code: {reset_code}\n\n"
            f"This code is valid for the next 10 minutes. If you did not request this password reset, "
            f"please ignore this email. Your account security remains unchanged.\n\n"
            f"To continue, enter the above code in the password reset page and follow the instructions.\n\n"
            f"Best regards,\n"
            f"Craigslist SafeBot Team"
        )
        email_handler.send_notification(to_emails=email_id, content=reset_email_content, subject=subject)
        logging.info("Reset code successfully sent to Admin")
        return True, None

    def verify_reset_code(self, email_id, user_code):
        """
        Verify the reset code the user entered.
        Uses bcrypt for password hashing and comparison.
        """
        success, stored_code = knowledge_base.get_reset_code(email_id=email_id)
        if not success:
            flash(stored_code, "error")
            return False, None

        # Verify the password with bcrypt
        if bcrypt.checkpw(user_code.encode('utf-8'), stored_code.encode('utf-8')):
            return True, f"Reset code is valid!"
        else:
            # return False, "Invalid reset code!"
            flash("Invalid reset code!", "error")

        return False, None
    

