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
from user_profiling import UserProfiling
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
user_profiling = UserProfiling()

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
        email_id = form.loginId.data
        password = form.password.data
        # Authenticate user and create session
        success, result = auth_handler.authenticate_user(email_id, password)
        if success:
            session['admin_id'] = result.get("admin_id")
            #session['admin_email'] = email_id
            session['admin_email'] = result.get('email_id')  # Store admin email in session
            user = User(id=email_id)
            login_user(user)
            flash("Admin login successful!", "success")
            return redirect(url_for('project_account_login'))
        else:
            # flash("Invalid credentials. Please try again.", "error")
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
        email_id = request.form.get('email_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone_number = request.form.get('phone_number') or None
        affiliation = request.form.get('affiliation') or None

        # Validate form fields
        if not password or not confirm_password or not email_id:
            flash("All mandatory fields must be filled", "error")
            return redirect(url_for('create_account'))

        if not confirm_password == password:
            flash("Passwords do not match. Try again!", "error")
            return redirect(url_for('create_account'))

        success, message = knowledge_base.create_admin(password, email_id, phone_number, affiliation)
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
        success, project_details = knowledge_base.get_project_details(email)
        if not success:
            flash("Error retrieving project information. Please check your inputs and try again.", "error")
            return render_template('project_account_login.html')
        #print("PROJECT: ", project_details)
        project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, assigned_admin_id = project_details

        if success:
            session.update({
                'email': email,
                'app_password': app_password,
                'project': project_name,
                'project_keywords': keywords_data
            })

            print("Session variables: ", session)
            user = User(id=email)
            login_user(user)
            return redirect(url_for('index'))  # Redirect to the main dashboard or index
        else:
            flash("Error retrieving project information. Please check your inputs and try again.", "error")
            return render_template('project_account_login.html')
        
    return render_template('project_account_login.html')


@app.route('/project_creation', methods=['GET', 'POST'])
@login_required
def project_creation():
    if request.method == 'POST':
        email = request.form['email']
        project_name = request.form['project_name']
        app_password = request.form['password']
        ai_prompt_text = request.form.get('ai_prompt_text', '')
        response_frequency = int(request.form.get('response_frequency', 0))
        keywords_data_fetch = request.form['keywords_data']
        keywords_data = keywords_data_fetch.replace('""', '"')

        try:
            keywords_data_updated = json.loads(keywords_data) if keywords_data else []
        except json.JSONDecodeError:
            flash("Invalid keywords data", "error")
            return redirect(url_for('project_creation'))

        # Insert the project using the create_project method from KnowledgeBase
        success, message = knowledge_base.create_project(email_id=email,
                                                         project_name=project_name,
                                                         app_password=app_password,
                                                         ai_prompt_text=ai_prompt_text,
                                                         response_frequency=response_frequency,
                                                         keywords_data=json.dumps(keywords_data_updated),
                                                         assigned_admin_id=session['admin_id']
                                                         )

        flash(message, "success" if success else "error")
        if success:
            return redirect(url_for('project_account_login'))
        else:
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
        # conversations_score[thread_id] = score
        conversations_score[thread_id] = score[0] if isinstance(score, (list, tuple)) else score
        #grouped_emails[thread_id].append({'score': score[0]})

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


@app.route('/update_project', methods=['GET', 'POST'])
@login_required
def update_project():
    if 'email' not in session or 'project' not in session:
        flash("You need to be logged in to update project details.", "error")
        return redirect(url_for('project_account_login'))
    email = session['email']
    project_name = session['project']
    if request.method == 'GET':
        success, project_info = knowledge_base.get_project_details(email)
        if not success:
            flash(project_info, "error")
            return redirect(url_for('index'))
        project_details = {
            "project_id": project_info[0],
            "email_id": project_info[1],
            "project_name": project_info[2],
            "app_password": project_info[3],
            "ai_prompt_text": project_info[4],
            "response_frequency": project_info[5],
            "keywords_data": project_info[6],
            "assigned_admin_id": project_info[7]
        }

        return render_template('update_project.html', project_details=project_details)
    elif request.method == 'POST':
        ai_prompt_text = request.form['ai_prompt_text']
        response_frequency = request.form['response_frequency']
        success, message = knowledge_base.update_project(email, project_name, ai_prompt_text, response_frequency)
        if success:
            flash("Project details updated successfully.", "success")
            return redirect(url_for('index'))
            flash("Failed to update project details. ")
            return render_template('update_project.html')
        
@app.route('/update_account_profile', methods=['GET', 'POST'])
@login_required
def update_account_profile():
    #print("Session Data in update_account_profile:", session)  # Debug session data

    if 'admin_id' not in session:
        print("admin_id not in session")
        flash("You need to be logged in to update your account profile.", "error")
        return redirect(url_for('project_account_login'))

    login_id = session['admin_id']
    email_id = session['admin_email']

    #print("Session Data in update_account_profile:", session)  # Debug session data
    if request.method == 'GET':
        success, account_details = knowledge_base.get_admin_details(email_id)
        if not success:
            flash(account_details, "error")  # Display error message if fetching fails
            return redirect(url_for('index'))
        else:
            return render_template('update_account_profile.html', account_details=account_details)

    elif request.method == 'POST':
        phone_number = request.form.get('phone_number')
        affiliation = request.form.get('affiliation')
        email_id = request.form.get('email_id')  # Optional email_id update

        success, message = knowledge_base.update_admin_profile(
            login_id, phone_number, affiliation, email_id)
        print(f"Update status: {success}, message: {message}")
        if success:
            flash("Account profile updated successfully.", "success")
            return redirect(url_for('index'))
        else:
            flash("Failed to update account profile.", "error")
            return render_template('update_account_profile.html', account_details={
                'phone_number': phone_number,
                'affiliation': affiliation,
                'email_id': email_id})


@app.route('/user_profiles', methods=['GET'])
def user_profiles():
    all_users = user_profiling.get_all_users()
    success, user_scores = knowledge_base.fetch_scores_at_user_level()

    if success:
        return render_template("user_profiles.html", active_users=all_users, user_scores=user_scores)
    else:
        return jsonify({"error": "Error fetching data"}), 500

@app.route('/user_profiles/active_users', methods=['GET'])
def user_profiles_active_users():
    all_users = user_profiling.get_all_users()
    print(all_users)
    if all_users:
        return render_template(
            "user_profiles.html",
            chart="active_users",
            active_users=all_users,
        )
    else:
        return jsonify({"error": "Error fetching active users"}), 500

@app.route('/user_profiles/top_users', methods=['GET'])
def user_profiles_top_users():
    success, user_scores = knowledge_base.fetch_scores_at_user_level()
    #print("DEBUG App: User Scores:", user_scores)  # Add this line to check the data
    if not success:
        return jsonify({"error": "Error fetching user scores"}), 500
    return render_template(
        'user_profiles.html',
        chart='top_users',
        user_scores=user_scores
    )

@app.route('/user_profiles/time_period_users', methods=['GET'])
def user_profiles_time_period_users():
    return render_template('user_profiles.html', chart='time_period_users')

@app.route('/email_view', methods=['GET'])
def email_view():
    return render_template('email_view.html')

if __name__ == '__main__':
    app.run(debug=True)
