import json
import os
import re
from flask import Flask, flash, session, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from datetime import datetime
from email_handler import EmailHandler
from auth_handler import LoginForm, User, AuthHandler
from knowledge_base import KnowledgeBase
from response_generator import ResponseGenerator
from interaction_profiling import InteractionProfiling
from datetime import datetime, timedelta
from email_processor import EmailProcessor

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))  # Use environment variable or random key

# Initialize Login Manager for user authentication
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None

# Initialize all instances for managing functionalities
email_handler = EmailHandler()
knowledge_base = KnowledgeBase()
auth_handler = AuthHandler()
response_generator = ResponseGenerator()
interaction_profiling = InteractionProfiling()
email_processor = EmailProcessor()

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def get_id(self):
        return self.id

# Routes for login, logout and load user for login session management
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        loginId = form.loginId.data
        password = form.password.data
        # Authenticate user and create session
        if auth_handler.authenticate_user(loginId, password):
            session['admin_id'] = loginId
            session['user_id'] = loginId
            user = User(id=loginId)
            login_user(user)
            print(f"Session Data After Login: {session}")
            next_page = request.args.get('next') or url_for('project_account_login')
            flash("Login successful!", "success")
            return redirect(next_page)
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for('login'))
        #     return redirect(url_for('project_account_login'))
        # return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# Route for the Create Account page
@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        # Get form data
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email_id = request.form.get('email_id')
        phone_number = request.form.get('phone_number') or None
        affiliation = request.form.get('affiliation') or None

        # Validate form fields
        if not login_id or not password or not confirm_password or not email_id:
            flash("All mandatory fields must be filled", "error")
            return redirect(url_for('create_account.html'))

        if not confirm_password == password:
            flash("Passwords do not match. Try again!", "error")
            return redirect(url_for('create_account.html'))

        success, message = knowledge_base.create_admin(login_id, password, email_id, phone_number, affiliation)
        flash(message, "success" if success else "error")
        
        if success:
            return redirect(url_for('login'))
    
    return render_template('create_account.html')


# Route for project account login
@app.route('/project_account_login', methods=['GET', 'POST'])
@login_required
def project_account_login():
    if request.method == 'POST':
        email = request.form['email']
        password_success, password_result = knowledge_base.get_app_password(email)
        project_success, project_result = knowledge_base.get_project_name(email)
        keywords_success, keywords_result = knowledge_base.get_project_keywords(email, project_result[0] if project_success else None)

        if not password_success or not project_success or not keywords_success:
            flash("Error retrieving project information. Please check your inputs and try again.", "error")
            return render_template('project_account_login.html')
        
        if password_result:
            session.update({
                'email': email,
                'app_password': password_result[0],
                'project': project_result[0],
                'project_keywords': keywords_result
            })

            # print("Session variables: ", session)
            user = User(id=email)
            login_user(user)
            return redirect(url_for('index'))  # Redirect to the main dashboard or index
        else:
            flash("Unable to retrieve app password. Please check the email and try again.")
            return render_template('project_account_login.html')
        
    return render_template('project_account_login.html')


@app.route('/project_creation', methods=['GET', 'POST'])
@login_required
def project_creation():
    if request.method == 'POST':
        email = request.form['email']
        project_name = request.form['project_name']
        app_password = request.form['password']
        prompt_text = request.form.get('prompt_text', '')
        response_frequency = int(request.form.get('response_frequency', 0))
        keywords_data_fetch = request.form['keywords_data']
        keywords_data = keywords_data_fetch.replace('""', '"')
        #print(keywords_data)
        try:
            keywords_data_updated = json.loads(keywords_data) if keywords_data else []
        except json.JSONDecodeError:
            flash("Invalid keywords data", "error")
            return redirect(url_for('project_creation'))

        # Insert the project using the create_project method from KnowledgeBase
        success, message = knowledge_base.create_project(email_id=email,
                                                         project_name=project_name,
                                                         app_password=app_password,
                                                         prompt_text=prompt_text,
                                                         response_frequency=response_frequency,
                                                         keywords_data=json.dumps(keywords_data_updated),
                                                         assigned_admin_id=session['admin_id']
                                                         )

        flash(message, "success" if success else "error")
        if success:
            return redirect(url_for('project_account_login'))
        else:
            print("Login failed:", message)
            flash(message, "error")

    return render_template('project_creation.html')


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
    emails, grouped_emails, keywords = email_handler.fetch_emails_and_keywords(
        subject=subject, content=content,
        start_date=start_date, end_date=end_date,
        bidirectional_address=bidirectional_address
    ) if search_initiated or last_30_days or last_60_days else []
    
    # Process the grouped emails
    email_processor.process_grouped_emails(grouped_emails)

    # Add the score to each conversation
    conversations_score = {}
    for thread_id in grouped_emails:
        score_success, score = knowledge_base.get_interaction_score(thread_id=thread_id)
        if not score_success:
            print(score_success)
            continue
        # print("THE INTERACTION SCORE: ", score[0])
        conversations_score[thread_id] = score
        #grouped_emails[thread_id].append({'score': score[0]})

    print(conversations_score)

    # Filter emails by selected keyword
    if selected_keyword:
        grouped_emails = {key: details for key, details in grouped_emails.items()
                          if any(selected_keyword.lower() in email['subject'].lower() or
                                 selected_keyword.lower() in email['content'].lower() for email in details)}

    return render_template('index.html', emails=emails, keywords=keywords,
                           search_initiated=search_initiated, last_30_days=last_30_days,
                           last_60_days=last_60_days, conversations=grouped_emails,
                           conversations_score=conversations_score,
                           start_date=start_date, end_date=end_date)


def fetch_score():
    try:
        email_threads = knowledge_base.fetch_all_email_threads()
        conversations_score = {}
        for thread in email_threads:
            thread_id = thread["thread_id"]
            score = thread["interaction_score"]
            conversations_score[thread_id] = score  # Map thread ID to its score
        return conversations_score, None
    except Exception as error:
        print(f"Error fetching email threads: {error}")
        return {}, f"Error fetching email threads: {error}"

@app.route('/update_project', methods=['GET', 'POST'])
@login_required
def update_project():
    if 'email' not in session or 'project' not in session:
        flash("You need to be logged in to update project details.")
        return redirect(url_for('project_account_login'))
    email = session['email']
    project_name = session['project']
    if request.method == 'GET':
        success, project_details = knowledge_base.get_project_details(email, project_name)
        if not success:
            flash(project_details)
            return redirect(url_for('index'))
        return render_template('update_project.html', project_details=project_details)
    elif request.method == 'POST':
        prompt_text = request.form['prompt_text']
        response_frequency = request.form['response_frequency']
        success, message = knowledge_base.update_project(email, project_name, prompt_text, response_frequency)
        if success:
            flash("Project details updated successfully.")
            return redirect(url_for('index'))
            flash("Failed to update project details. ")
            return render_template('update_project.html')
        
@app.route('/update_account_profile', methods=['GET', 'POST'])
@login_required
def update_account_profile():
    print("Session Data in update_account_profile:", session)  # Debug session data

    if 'admin_id' not in session:
        print("admin_id not in session")
        flash("You need to be logged in to update your account profile.")
        return redirect(url_for('project_account_login'))

    login_id = session['admin_id']

    print(login_id)
    print("Session Data in update_account_profile:", session)  # Debug session data
    if request.method == 'GET':
        success, account_details = knowledge_base.get_account_profile(login_id)
        if not success:
            flash(account_details)  # Display error message if fetching fails
            return redirect(url_for('index'))
        else:
            return render_template('update_account_profile.html', account_details=account_details)

    elif request.method == 'POST':
        phone_number = request.form.get('phone_number')
        affiliation = request.form.get('affiliation')
        email_id = request.form.get('email_id')  # Optional email_id update

        success, message = knowledge_base.update_account_profile(
            login_id, phone_number, affiliation, email_id)
        print(f"Update status: {success}, message: {message}")
        if success:
            flash("Account profile updated successfully.")
            return redirect(url_for('index'))
        else:
            flash("Failed to update account profile. ")
            return render_template('update_account_profile.html', account_details={
                'phone_number': phone_number,
                'affiliation': affiliation,
                'email_id': email_id})

@app.route('/user_profiles')
def user_profiles():
    # Redirect to active users as the default
    return redirect(url_for('user_profiles_active_users'))

@app.route('/user_profiles/active_users')
def user_profiles_active_users():
    return render_template('user_profiles.html', chart='active_users')

@app.route('/user_profiles/top_users')
def user_profiles_top_users():
    return render_template('user_profiles.html', chart='top_users')

@app.route('/user_profiles/time_period_users')
def user_profiles_time_period_users():
    return render_template('user_profiles.html', chart='time_period_users')

@app.route('/email_view')
def email_view():
    return redirect(url_for('user_profiles_active_users'))
    # return render_template('email_view.html')

if __name__ == '__main__':
    app.run(debug=True)
