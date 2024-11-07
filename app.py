import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from wtforms.validators import DataRequired
from email_handler import EmailHandler
from auth_handler import LoginForm, User, load_user, authenticate_user
from response_generator import generate_response
from datetime import datetime, timedelta

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))  # Use environment variable or random key

# Initialize Login Manager for user authentication
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None

# Initialize EmailHandler for managing email-related functionalities
email_handler = EmailHandler()


# User loader for login session management
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# Routes for login and logout
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        loginId = form.loginId.data
        password = form.password.data

        # Authenticate user and create session
        if authenticate_user(loginId, password):
            user = User(id=loginId)
            login_user(user)
            return redirect(url_for('index'))
        return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def generate_and_send_response(emails, message_id):
    """
    Fetch the email by message_id, generate a response using LLM, and send the reply.
    """
    # Step 1: Fetch emails and find the specified email
    email = next((e for e in emails if e['message_id'] == message_id), None)
    
    if not email:
        print("Email not found.")
        return
    
    # Step 2: Clean the email body
    clean_content = email['content']
    
    # Step 3: Generate response
    prompt = "You are a police detective and posted an ad saying you are looking to buy watches at a cheap price in hope of catching some criminals. You received an email as below:"
    response_text = generate_response(prompt, clean_content)
    
    # Step 4: Send the response as a reply
    to_address = email['from']
    subject = email['subject']
    references = email['references']
    email_handler.send_email(
        to_address=to_address,
        content=response_text,
        message_id=email['message_id'],
        references=references,
        subject=subject
    )

    print("Response sent successfully.")
    return 

# Main route to display emails and conversations
@app.route('/', methods=['GET'])
@login_required
def index():
    search_initiated = 'search' in request.args
    last_30_days = 'last_30_days' in request.args
    last_60_days = 'last_60_days' in request.args

    # Get search parameters
    subject = request.args.get('subject')
    content = request.args.get('content')
    selected_keyword = request.args.get('keyword')
    bidirectional_address = request.args.get('email')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Set default dates to last 30 days if no date filter is applied
    if not search_initiated and not last_30_days and not last_60_days:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        last_30_days = True  # Ensure the button state is correct for initial load

    # Fetch, filter, and group emails
    emails = email_handler.fetch_emails(
        subject=subject, content=content,
        start_date=start_date, end_date=end_date,
        bidirectional_address=bidirectional_address
    ) if search_initiated or last_30_days or last_60_days else []

    # Call function to generate and send a response for a specific email
    #generate_and_send_response(emails, "<CAPBq5+2wXNpAfhTjaKD8aPEW+bL__8ryV=Lt108Qrmh26aR4rQ@mail.gmail.com>")

    grouped_emails = email_handler.group_emails_by_conversation(emails)
    keywords = email_handler.extract_keywords(emails) if emails else []

    # Filter emails by selected keyword
    if selected_keyword:
        grouped_emails = {key: details for key, details in grouped_emails.items()
                          if any(selected_keyword.lower() in email['subject'].lower() or
                                 selected_keyword.lower() in email['content'].lower() for email in details)}

    return render_template('index.html', emails=emails, keywords=keywords,
                           search_initiated=search_initiated, last_30_days=last_30_days,
                           last_60_days=last_60_days, conversations=grouped_emails,
                           start_date=start_date, end_date=end_date)


if __name__ == '__main__':
    app.run(debug=True)
