import json
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
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
from project_scheduler import ProjectScheduler

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))  # Use environment variable or random key

# Configure logging centrally
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info(f"Logging is configured.")

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
project_scheduler = ProjectScheduler()

logging.info(f"Starting the project!!")
scheduler = BackgroundScheduler()
scheduler.start()
# Schedule the `process_emails` function to run every 15 seconds
try:
    scheduler.add_job(
        func=project_scheduler.process_projects,
        trigger=IntervalTrigger(minutes=20),
        id='email_processing_job',  # Unique identifier for the job
        replace_existing=True,
        next_run_time=datetime.now()  # Schedule the first run to start immediately
    )
except Exception as e:
    logging.error(f"Failed to add scheduler job: {e}")


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
            return redirect(url_for('all_projects_view'))
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
#
#
# # Route for project account login
# @app.route('/project_account_login', methods=['GET', 'POST'])
# @login_required
# def project_account_login():
#     if request.method == 'POST':
#         email = request.form['email']
#         success, project_details = knowledge_base.get_project_details(email)
#         if not success:
#             flash("Error retrieving project information. Please check your inputs and try again.", "error")
#             return render_template('project_account_login.html')
#         #logging.info(f"PROJECT: {project_details}")
#         project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id = project_details
#
#         if success:
#             session.update({
#                 'email': email,
#                 'app_password': app_password,
#                 'project': project_name,
#                 'project_keywords': keywords_data
#             })
#
#             logging.info(f"Session variables: {session}")
#             user = User(id=email)
#             login_user(user)
#             return redirect(url_for('index'))  # Redirect to the main dashboard or index
#         else:
#             flash("Error retrieving project information. Please check your inputs and try again.", "error")
#             return render_template('project_account_login.html')
#
#     return render_template('project_account_login.html')


@app.route('/project_creation', methods=['GET', 'POST'])
@login_required
def project_creation():
    if request.method == 'POST':
        email = request.form['email']
        project_name = request.form['project_name']
        app_password = request.form['password']
        ai_prompt_text = request.form.get('ai_prompt_text', '')
        response_frequency_raw = request.form.get('response_frequency', '10').strip()
        response_frequency = 10 if not response_frequency_raw.isdigit() else int(response_frequency_raw)
        keywords_data_fetch = request.form['keywords_data']
        keywords_data = keywords_data_fetch.replace('""', '"')

        project_success, message = knowledge_base.is_email_unique_in_projects(email)
        if not project_success:
            flash(message, "error")
            return redirect(url_for('project_creation'))

        # Verify app password
        try:
            email_handler.login_to_email(email, app_password)
        except ValueError:
            flash("Email or app password is missing.", "error")
            return redirect(url_for('project_creation'))
        except Exception as e:
            logging.error(f"Failed to verify app password: {e}")
            flash("Invalid app password or unable to connect to the email server. Please try again.", "error")
            return redirect(url_for('project_creation'))

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
                                                         owner_admin_id=session['admin_id'],
                                                         last_updated=None
        )

        flash(message, "success" if success else "error")
        if success:
            # return redirect(url_for('project_account_login'))
            return redirect(url_for('all_projects_view'))
        else:
            flash(message, "error")

    return render_template('project_creation.html')

@app.route('/update_project', methods=['GET', 'POST'])
@login_required
def update_project():
    if 'email' not in session or 'project' not in session:
        flash("You need to be logged in to update project details.", "error")
        # return redirect(url_for('project_account_login'))
        return redirect(url_for('all_projects_view'))
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
            "owner_admin_id": project_info[7]
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
    #logging.info(f"Session Data in update_account_profile: {session}")  # Debug session data

    if 'admin_id' not in session:
        logging.error(f"admin_id not in session")
        flash("You need to be logged in to update your account profile.", "error")
        # return redirect(url_for('project_account_login'))
        return redirect(url_for('all_projects_view'))
    login_id = session['admin_id']
    email_id = session['admin_email']

    #logging.info(f"Session Data in update_account_profile: {session}")  # Debug session data
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
        logging.info(f"Update status: {success}, message: {message}")
        if success:
            flash("Account profile updated successfully.", "success")
            return redirect(url_for('index'))
        else:
            flash("Failed to update account profile.", "error")
            return render_template('update_account_profile.html', account_details={
                'phone_number': phone_number,
                'affiliation': affiliation,
                'email_id': email_id})

# @app.route('/all_projects_view', methods=['GET', 'POST'])
# @login_required
# def all_projects_view():
#     """
#     Display all projects and allow the user to select or create a new project.
#     """
#     # Fetch all projects from the database
#     success, projects = knowledge_base.fetch_all_projects()
#     if not success:
#         return render_template('error.html', message=projects), 500  # Display error if fetch fails
#
#
#     # Get search query from the request
#     search_query = request.args.get('search_query')
#     if search_query:
#     # Filter projects based on the query
#         filtered_projects = [
#             project for project in projects
#             if search_query.lower() in project[2].lower() or search_query.lower() in project[1].lower()
#         ]
#         if not filtered_projects:
#             flash("Project doesn't exist. Please try again!", "danger")
#             filtered_projects = []
#     else:
#         filtered_projects = projects
#
#     # Format the filtered projects for rendering
#     formatted_projects = [
#         {
#             "id": project[0],  # project_id
#             "email": project[1],  # email_id
#             "name": project[2],  # project_name
#             "last_updated": project[8],  # last_updated as date
#         }
#         for project in filtered_projects
#     ]
#
#     if request.method == 'POST':
#         # Get selected project's email from the form
#         email = request.form['email']
#
#         # Fetch project details by email
#         success, project_details = knowledge_base.get_project_details(email)
#         if not success:
#             flash("Error retrieving project information. Please check your inputs and try again.", "danger")
#             return redirect(url_for('all_projects_view'))
#
#         # Extract project details
#         project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, last_updated= project_details
#
#         # Update session with selected project details
#         session.update({
#             'email': email_id,
#             'app_password': app_password,
#             'project': project_name,
#             'project_keywords': keywords_data
#         })
#
#         logging.info(f"Session variables updated: {session}")
#         user = User(id=email_id)
#         login_user(user)
#
#         # Redirect to the main dashboard (index)
#         return redirect(url_for('index'))
#
#     return render_template('all_projects_view.html', projects=formatted_projects, search_query=search_query)


@app.route('/all_projects_view', methods=['GET', 'POST'])
@login_required
def all_projects_view():
    logging.info(f"Session Admin ID: {session.get('admin_id')}")
    """
    Display all projects and allow the user to select or create a new project.
    """
    # Fetch all projects from the database
    success, projects = knowledge_base.fetch_all_projects()

    if not success:
        return render_template('error.html', message=projects), 500  # Display error if fetch fails

    # Get search query from the request
    search_query = request.args.get('search_query')
    filtered_projects = projects

    if search_query:
        # Filter projects based on the query
        filtered_projects = [
            project for project in projects
            if search_query.lower() in project[2].lower() or search_query.lower() in project[1].lower()
        ]
        # If no matching projects are found, flash an error message
        if not filtered_projects:
            flash("No projects found. Please create or view another project.", "danger")

    # Format the filtered projects for rendering
    formatted_projects = [
        {
            "id": project[0],  # project_id
            "email": project[1],  # email_id
            "name": project[2],  # project_name
            "last_updated": project[8],  # last_updated as date,
            "owner_admin_id": project[7],  # owner_admin_id
        }
        for project in filtered_projects
    ]
    if request.method == 'POST':
        # Get selected project's email from the form
        email = request.form['email']
        # Fetch project details by email
        success, project_details = knowledge_base.get_project_details(email)
        if not success:
            flash("Error retrieving project information. Please check your inputs and try again.", "danger")
            return redirect(url_for('all_projects_view'))

        # Extract project details
        project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, last_updated = project_details
        logging.info(f"Project Owner ID: {owner_admin_id}, Session Admin ID: {session.get('admin_id')}")

        # Update session with selected project details
        session.update({
            'email': email_id,
            'app_password': app_password,
            'project': project_name,
            'project_keywords': keywords_data
        })

        logging.info(f"Session variables updated: {session}")
        user = User(id=email_id)
        login_user(user)

        # Redirect to the main dashboard (index)
        return redirect(url_for('index'))

    return render_template('all_projects_view.html', projects=formatted_projects, search_query=search_query)

#
# @app.route('/delete_project/<email>', methods=['POST'])
# @login_required
# def delete_project(email):
#     """
#     Deletes a project if the logged-in admin is the owner.
#     """
#     # Get the admin ID from the session
#     current_admin_id = session.get('admin_id')
#
#     # Fetch project details by email
#     success, project_details = knowledge_base.get_project_details(email)
#     if not success:
#         flash("Project not found or failed to retrieve project details.", "danger")
#         return redirect(url_for('all_projects_view'))
#
#     # Extract project owner ID from the details
#     owner_admin_id = project_details.get('owner_admin_id')
#
#     # Check if the logged-in admin is the owner
#     if current_admin_id != owner_admin_id:
#         flash("You are not authorized to delete this project.", "danger")
#         return redirect(url_for('all_projects_view'))
#
#     # Perform deletion
#     delete_success, message = knowledge_base.delete_project(email)
#     if delete_success:
#         flash("Project deleted successfully.", "success")
#     else:
#         flash(f"Failed to delete the project: {message}", "danger")
#
#     return redirect(url_for('all_projects_view'))

@app.route('/update_thread_state', methods=['POST'])
@login_required
def update_thread_state():
    data = request.get_json()
    thread_id = data.get('thread_id')
    new_state = data.get('new_state')

    if not thread_id or not new_state:
        return jsonify({"success": False, "message": "Thread ID and state are required."}), 400

    success, message = knowledge_base.update_ai_response_state(thread_id, new_state)
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 500


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
    logging.info(all_users)
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
    #logging.info(f"DEBUG App: User Scores: {user_scores}")  # Add this line to check the data
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
#
#
# # Main route to display emails and conversations
# @app.route('/', methods=['GET'])
# @login_required
# def index():
#     filters = {
#         'search_initiated': 'search' in request.args,
#         'last_30_days': 'last_30_days' in request.args,
#         'last_60_days': 'last_60_days' in request.args,
#         'subject': request.args.get('subject'),
#         'content': request.args.get('content'),
#         'selected_keyword': request.args.get('keyword'),
#         'bidirectional_address': request.args.get('email'),
#         'start_date': request.args.get('start_date'),
#         'end_date': request.args.get('end_date')
#     }
#
#     # Call process_emails with parameters
#     data = project_scheduler.process_projects(filters, session['email'], session['app_password'])
#     return render_template('index.html', **data)

@app.route('/', methods=['GET'])
@login_required
def index():
    filters = {
        'search_initiated': 'search' in request.args,
        'last_30_days': 'last_30_days' in request.args,
        'last_60_days': 'last_60_days' in request.args,
        'subject': request.args.get('subject'),
        'content': request.args.get('content'),
        'selected_keyword': request.args.get('keyword'),
        'bidirectional_address': request.args.get('email'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date')
    }

    # Use session variables to process the selected project
    if 'email' not in session or 'app_password' not in session:
        flash("No project selected. Please select a project.", "danger")
        return redirect(url_for('all_projects_view'))

    data = project_scheduler.process_projects(filters, session['email'], session['app_password'])
    return render_template('index.html', **data)


if __name__ == '__main__':
    app.run(debug=True)

