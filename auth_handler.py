import yaml
import os
import psycopg2
import bcrypt
from flask import flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import UserMixin


# Database connection function
def get_db_connection():
    """
    Connect to PostgreSQL using credentials stored in 'credentials.yaml'.
    Returns a connection object.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(project_root, "credentials.yaml")

    with open(credentials_path) as f:
        my_credentials = yaml.load(f, Loader=yaml.FullLoader)

    pg_config = my_credentials['postgresql']

    try:
        conn = psycopg2.connect(
            host=pg_config['pg_host'],
            database=pg_config['pg_database'],
            user=pg_config['pg_user'],
            password=pg_config['pg_password'],
            port=pg_config.get('pg_port', 5432)
        )
        return conn
    except Exception as error:
        print("Error while connecting to PostgreSQL:", error)
        return None


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


# User loader function
def load_user(user_id):
    """
    Load user from session using user ID.
    """
    return User(user_id)


# Authentication function
def authenticate_user(loginId, password):
    """
    Authenticate the user by verifying the login ID and password.
    Uses bcrypt for password hashing and comparison.
    """
    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed.")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admin_accounts WHERE login_id = %s", (loginId,))
        result = cursor.fetchone()

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

    except Exception as error:
        flash("Database error:", error)
        return False

    finally:
        cursor.close()
        conn.close()
