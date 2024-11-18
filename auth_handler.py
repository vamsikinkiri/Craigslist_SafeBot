import bcrypt
from knowledge_base import KnowledgeBase
from flask import flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import UserMixin

knowledge_base = KnowledgeBase()

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
    def authenticate_user(self, loginId, password):
        """
        Authenticate the user by verifying the login ID and password.
        Uses bcrypt for password hashing and comparison.
        """
        success, result = knowledge_base.get_password(loginId)
        if not success:
            flash(result)
            return False

        if result:
            stored_password = result[0]
            # Verify the password with bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                return True
            else:
                flash("Invalid password.")
        else:
            flash("User not found.")
        return False
