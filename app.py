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

# Secure session cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies

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
            session['admin_affiliation'] = result.get('affiliation')
            session['admin_contact_number'] = result.get('contact_number')
            user = User(id=email_id)
            login_user(user)
            # flash("Admin login successful!", "success")
            return redirect(url_for('all_projects_view'))
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

        if success:
            return redirect(url_for('login'))
        else:
            flash(message, "error")

    return render_template('create_account.html')

@app.route('/project_creation', methods=['GET', 'POST'])
@login_required
def project_creation():
    # Define the default criteria outside the conditional blocks
    default_switch_manual_criterias = [
        "The suspect did not stop the conversation after discovering our age.",
        "The suspect requests a photograph of the person we are pretending to be.",
        "The suspect suggests communicating via phone number or alternative platforms.",
    ]
    if request.method == 'POST':
        email = request.form['email']
        project_name = "Project - " + request.form['project_name']
        app_password = request.form['password']
        ai_prompt_text = request.form.get('ai_prompt_text', '')
        response_frequency_raw = request.form.get('response_frequency', '10').strip()
        response_frequency = 10 if not response_frequency_raw.isdigit() else int(response_frequency_raw)
        keywords_data_fetch = request.form['keywords_data']
        keywords_data = keywords_data_fetch.replace('""', '"')
        lower_threshold_raw = request.form.get('lower_threshold', '0').strip()
        upper_threshold_raw = request.form.get('upper_threshold', '75').strip()
        lower_threshold = 0 if not lower_threshold_raw.isdigit() else int(lower_threshold_raw)
        upper_threshold = 75 if not upper_threshold_raw.isdigit() else int(upper_threshold_raw)
        authorized_emails = request.form.get('authorized_emails', '[]')
        POSED_NAME_DEFAULT = "Karen"
        POSED_AGE_DEFAULT = 16
        POSED_SEX_DEFAULT = "Female"
        POSED_LOCATION_DEFAULT = "Riverside"
        posed_name = request.form.get('posed_name', POSED_NAME_DEFAULT)
        posed_age = int(request.form.get('posed_age_default', POSED_AGE_DEFAULT))
        posed_sex = request.form.get('posed_sex', POSED_SEX_DEFAULT)
        posed_location = request.form.get('posed_location', POSED_LOCATION_DEFAULT)

        # Process additional criteria from form
        try:
            new_criterias_raw = request.form.get('criteria_data', '[]')  # Hidden input field
            new_criterias = parse_json_field(new_criterias_raw, [])
            if not isinstance(new_criterias, list):
                raise ValueError("Criteria must be a list.")
        except json.JSONDecodeError:
            flash("Invalid criteria format", "error")
            return redirect(url_for('project_creation'))

        # Combine default and user-added criteria
        switch_manual_criterias = default_switch_manual_criterias + new_criterias


        try:
            authorized_emails_list = json.loads(authorized_emails)
            if not isinstance(authorized_emails_list, list):
                raise ValueError("Authorized emails must be a list.")
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid email format"}), 400
        # authorized_emails=["vamsikinkiri@gmail.com", "kinkiriv@gmail.com"]

        # try:
        #     switch_manual_criterias_list = json.loads(switch_manual_criterias)
        #     if not isinstance(switch_manual_criterias_list, list):
        #         raise ValueError("Switch manual criterias must be a list.")
        # except json.JSONDecodeError:
        #     return jsonify({"error": "Invalid criterias format"}), 400

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

        # Insert the project into KnowledgeBase
        success, message = knowledge_base.create_project(email_id=email,
                                                         project_name=project_name,
                                                         app_password=app_password,
                                                         ai_prompt_text=ai_prompt_text,
                                                         response_frequency=response_frequency,
                                                         keywords_data=json.dumps(keywords_data_updated),
                                                         owner_admin_id=session['admin_id'],
                                                         lower_threshold=lower_threshold,
                                                         upper_threshold=upper_threshold,
                                                         authorized_emails=authorized_emails_list,
                                                         posed_name=posed_name,
                                                         posed_age=posed_age,
                                                         posed_sex=posed_sex,
                                                         posed_location=posed_location,
                                                         switch_manual_criterias=switch_manual_criterias,
                                                         )

        if success:
            return redirect(url_for('all_projects_view'))
        else:
            flash(message, "error")

    return render_template(
        'project_creation.html',
        default_switch_manual_criterias=default_switch_manual_criterias
    )

@app.route('/api/update_projects', methods=['GET'])
@login_required
def update_projects():
    # Use the function in knowledge base to get all projects
    success, projects = knowledge_base.fetch_all_projects()
    if not success:
        return jsonify({"success": False, "message": projects}), 500

    projects_list = [
        {
            "project_id": project[0],
            "project_name": project[2],
            "ai_prompt_text": project[4]
        }
        for project in projects
    ]
    return jsonify({"success": True, "projects": projects_list})

def parse_json_field(field, default):
    try:
        return json.loads(field) if field else default
    except json.JSONDecodeError:
        return default
    
def get_project_data(email):
    try:
        # Fetch project details using the knowledge base
        success, project_info = knowledge_base.get_project_details(email)
        if not success:
            logging.error(f"Failed to fetch project details for email: {email}. Reason: {project_info}")
            return success, project_info

        # Parse JSON fields safely
        try:
            if isinstance(project_info[6], dict):
                keywords_data = project_info[6]
            else:
                keywords_data = parse_json_field(project_info[6], {})

            # Handle authorized_emails (stored as a JSON-like string)
            if isinstance(project_info[10], list):  # Already a list
                authorized_emails = project_info[10]
            elif isinstance(project_info[10], str):  # Parse string representation of list
                authorized_emails = json.loads(project_info[10])
            else:
                authorized_emails = []



        except Exception as parse_error:
            logging.error(f"Error parsing JSON fields for project: {project_info[0]} - {parse_error}")
            return False, "Error parsing project JSON fields."
        logging.info(f"Get data 1: {keywords_data}")
        logging.info(f"Get email 1: {authorized_emails}")

        # Build and return project data
        project_data = {
            "project_id": project_info[0],
            "email_id": project_info[1],
            "project_name": project_info[2],
            "app_password": project_info[3],
            "ai_prompt_text": project_info[4],
            "response_frequency": project_info[5],
            "keywords_data": keywords_data,
            "owner_admin_id": project_info[7],
            "lower_threshold": project_info[8],
            "upper_threshold": project_info[9],
            "authorized_emails": authorized_emails,
            "posed_name": project_info[11],
            "posed_age": project_info[12],
            "posed_sex": project_info[13],
            "posed_location": project_info[14],
            "switch_manual_criterias": project_info[15],
            "last_updated": project_info[16]
        }
        logging.info(f"Successfully processed project data for email: {email}")
        logging.info(f"Get criterias 1: {project_info[15]}")
        return True, project_data

    except Exception as e:
        logging.error(f"Unexpected error while fetching or processing project data for email {email}: {e}")
        return False, "Error processing project data."


@app.route('/update_project', methods=['GET', 'POST'])
@login_required
def update_project():
    if 'email' not in session or 'project' not in session:
        flash("You need to be logged in to update project details.", "error")
        return redirect(url_for('all_projects_view'))
    email = session['email']
    project_name = session['project']

    if request.method == 'GET':
        try:
            # Fetch project details
            success, project_details = get_project_data(email)
            if not success:
                flash(project_details, "error")
                return redirect(url_for('index'))

            # Log project details for debugging
            logging.info(f"Fetched project details: {project_details}")
            # Fetch all projects for prompts
            all_projects_success, all_projects = knowledge_base.fetch_all_projects()
            if not all_projects_success:
                flash(all_projects, "error")
                all_projects = []

            projects_with_prompts = [
                {
                    "project_id": project[0],
                    "project_name": project[2],
                    "ai_prompt_text": project[4],
                }
                for project in all_projects
            ]
            return render_template(
                'update_project.html',
                project_details=project_details,
                projects=projects_with_prompts,
            )
        except Exception as e:
            logging.error(f"Error during GET request for update_project: {e}")
            flash("An error occurred while fetching project details.", "error")
            return redirect(url_for('index'))

    elif request.method == 'POST':
        try:
            logging.info(f"Form data received: {request.form}")

            # Fetch project info
            success, project_info = get_project_data(email)
            if not success:
                flash(project_info, "error")
                return redirect(url_for('index'))

            # Log fetched project info
            logging.info(f"Fetched project info for update: {project_info}")

            # Parse form data
            mode = request.form.get('mode')
            response_frequency = int(request.form.get('response_frequency', project_info.get('response_frequency', 0)))
            lower_threshold = int(request.form.get('lower_threshold', project_info.get('lower_threshold', 0)))
            upper_threshold = int(request.form.get('upper_threshold', project_info.get('upper_threshold', 100)))
            # Validate thresholds
            if lower_threshold >= upper_threshold:
                flash(f"Lower threshold ({lower_threshold}) must be less than upper threshold ({upper_threshold}).", "error")
                return redirect(url_for('update_project'))

            # Parse updated keywords from the form
            updated_keywords_data = request.form.get('keywords_data', '{}')
            updated_keywords_raw = parse_json_field(updated_keywords_data, {})  # Parse updated keywords from the frontend
            existing_keywords = project_info.get('keywords_data', {})  # Existing keywords in the backend
            final_keywords = {
                key: updated_keywords_raw[key]  # Use updated value if it exists in the frontend
                for key in updated_keywords_raw }
            for key in existing_keywords:
                if key not in updated_keywords_raw:  # If the key is not in the updated list, retain it
                    final_keywords[key] = existing_keywords[key]
            updated_keywords = final_keywords  # Final result for backend storage

            # Parse updated emails from the form
            updated_emails_data = request.form.get('authorized_emails', '[]')
            updated_emails_raw = parse_json_field(updated_emails_data, [])
            updated_emails = list(set(updated_emails_raw))

            # logging.info(f"Form data received: {request.form}")
            # logging.info(f"Raw switch_manual_criterias: {new_switch_manual_criterias}, type: {type(new_switch_manual_criterias)}")
            existing_criterias = project_info.get('switch_manual_criterias', '[]')
            if isinstance(existing_criterias, str):
                existing_criterias = parse_json_field(existing_criterias, [])

            new_switch_manual_criterias = request.form.get('switch_manual_criterias', '[]')
            if new_switch_manual_criterias:
                try:
                    # Parse JSON from the request form field
                    parsed_criterias = parse_json_field(new_switch_manual_criterias, []) if isinstance(new_switch_manual_criterias, str) else new_switch_manual_criterias

                    if not isinstance(parsed_criterias, list):
                        raise ValueError(f"Parsed criterias must be a list, got {type(parsed_criterias)} instead.")
                    updated_criterias = list(set(parsed_criterias))
                except ValueError as e:
                    logging.error(f"Failed to parse switch_manual_criterias: {e}")
                    updated_criterias  = []
            else:
                updated_criterias = existing_criterias
            # Final updated criterias
            switch_manual_criterias = updated_criterias

            # Handle AI prompt text
            ai_prompt_text = (
                request.form.get('ai_prompt_text') if mode == 'edit'
                else request.form.get('sample_prompt', project_info.get('ai_prompt_text', ''))
            )

            posed_name = request.form.get('posed_name', project_info.get('posed_name', ''))
            posed_age = int(request.form.get('posed_age', project_info.get('posed_age', 0)))
            posed_sex = request.form.get('posed_sex', project_info.get('posed_sex', ''))
            posed_location = request.form.get('posed_location', project_info.get('posed_location', ''))

            # Parse and process manual criteria
            # Update project details in the knowledge base
            success, message = knowledge_base.update_project(
                email=email,
                project_name=project_name,
                ai_prompt_text=ai_prompt_text,
                response_frequency=response_frequency,
                keywords_data=json.dumps(updated_keywords),  # Ensure data is serialized
                lower_threshold=lower_threshold,
                upper_threshold=upper_threshold,
                authorized_emails=json.dumps(updated_emails),  # Ensure data is serialized
                # Make sure to update these after frontend changes are done
                posed_name=posed_name,
                posed_age=posed_age,
                posed_sex=posed_sex,
                posed_location=posed_location,
                switch_manual_criterias=json.dumps(switch_manual_criterias)
            )

            if success:
                #flash("Project details updated successfully.", "success")
                return redirect(url_for('index'))
            else:
                flash(message, "error")
                return redirect(url_for('update_project'))
        except json.JSONDecodeError as json_error:
            logging.error(f"JSON decoding error: {json_error}")
            flash("An error occurred while processing the project data.", "error")
            return redirect(url_for('update_project'))
        except Exception as e:
            logging.error(f"Unexpected error during project update: {e}")
            flash("An unexpected error occurred while updating the project.", "error")
            return redirect(url_for('update_project'))

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
            # flash("Account profile updated successfully.", "success")
            return redirect(url_for('index'))
        else:
            flash("Failed to update account profile.", "error")
            return render_template('update_account_profile.html', account_details={
                'phone_number': phone_number,
                'affiliation': affiliation,
                'email_id': email_id})


@app.route('/all_projects_view', methods=['GET', 'POST'])
@login_required
def all_projects_view():
    """
    Display all projects and allow the user to select or create a new project.
    """
    logging.info(f"Session Admin ID: {session.get('admin_id')}")
    # Fetch all projects from the database
    success, projects = knowledge_base.fetch_all_projects()

    if not success:
        return render_template('error.html', message=projects), 500  # Display error if fetch fails
    # Get search query from the request
    search_query = request.args.get('search_query')
    filtered_projects = projects

    authorized_projects = [project for project in projects if session['admin_email'] in project[10]]
    unauthorized_projects = [project for project in projects if session['admin_email'] not in project[10]]

    logging.info(f"Authorized Projects created are: {authorized_projects}")
    logging.info(f"Unauthorized Projects created are: {unauthorized_projects}")

    search_query = request.args.get('search_query', "").strip().lower()
    if search_query:
        authorized_projects = [
            project for project in authorized_projects
            if search_query in project[2].lower() or search_query in project[1].lower()
        ]
        unauthorized_projects = [
            project for project in unauthorized_projects
            if search_query in project[2].lower() or search_query in project[1].lower()
        ]
        if not authorized_projects and not unauthorized_projects:
            flash("No projects found. Please try a different search.", "error")

    # Format the filtered projects for rendering
    formatted_projects = [
        {
            "id": project[0],  # project_id
            "email": project[1],  # email_id
            "name": project[2],  # project_name
            "last_updated": project[16],  # last_updated as date,
            "owner_admin_id": project[7],  # owner_admin_id
        }
        for project in filtered_projects
    ]
    if request.method == 'POST':
        # Handle 'Request Access' or 'Open Project' actions
        project_id = request.form.get('project_id')
        email = request.form.get('email')
        logging.info(f"POST action with project_id: {project_id}, email: {email}")

        if project_id:
            # Request Access: Notify admins for unauthorized projects
            project = next((p for p in unauthorized_projects if p[0] == project_id), None)
            if project:
                project_scheduler.notify_admins_of_access_request(project_details=project)
                flash("Access request sent to project admins.", "info")
            else:
                flash("Project not found in unauthorized projects.", "error")
        elif email:
            # Open Project: Update session and redirect
            success, project_details = knowledge_base.get_project_details(email)
            if success and project_details:
                # Extract project details
                (
                    project_id, email_id, project_name, app_password, ai_prompt_text,
                    response_frequency, keywords_data, owner_admin_id, lower_threshold,
                    upper_threshold, authorized_emails, posed_name, posed_age, posed_sex,
                    posed_location, switch_manual_criterias, last_updated
                ) = project_details

                # Update session variables
                session.update({
                    'project_id': project_id,
                    'email': email_id,
                    'app_password': app_password,
                    'project': project_name,
                    'project_keywords': keywords_data
                })
                logging.info(f"Session updated: {session}")
                return redirect(url_for('index'))
            else:
                flash("Error retrieving project information. Please try again.", "error")
        else:
            flash("No valid action selected. Please try again.", "error")
        current_admin_id = session.get('admin_id')
    return render_template(
        'all_projects_view.html',
        authorized_projects=authorized_projects,
        unauthorized_projects=unauthorized_projects,
        search_query=search_query,
        current_admin_id=session.get('admin_id')
    )

@app.route('/delete_project/<string:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    """
    Delete a project if the current admin is the owner.
    """
    # Fetch project details by ID
    success, project_details = knowledge_base.get_project_details_by_id(project_id)
    if not success:
        flash("Error retrieving project details: " + project_details, "error")
        return redirect(url_for('all_projects_view'))

    # Extract owner_admin_id from project_details tuple owner_admin_id
    project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, lower_threshold, upper_threshold, authorized_emails, posed_name, posed_age, posed_sex, posed_location, switch_manual_criterias, last_updated  = project_details

    # Check if the current session's admin_id matches the owner_admin_id
    session_admin_id = session.get('admin_id')
    if session_admin_id != owner_admin_id:
        flash("You do not have permission to delete this project.", "error")
        return redirect(url_for('all_projects_view'))

    # Delete the project
    delete_success, message = knowledge_base.delete_project(project_id)
    if not delete_success:
        flash("Error deleting project: " + message, "error")
        return redirect(url_for('all_projects_view'))

    # flash("Project deleted successfully.", "success")
    return (redirect(url_for('all_projects_view')))


@app.route('/user_profiles', methods=['GET'])
def user_profiles():
    """
    Fetch and display suspect profiles with sorting and filtering by last active time.
    """
    # Fetch all suspect profiles
    all_users = user_profiling.get_all_users()
    success, user_scores = knowledge_base.fetch_scores_at_user_level(project_id=session['project_id'])

    if not all_users:
        return jsonify({"error": "Error fetching suspect profiles"}), 500

    # Handle 'last_active_filter' query parameter
    last_active_filter = request.args.get("last_active_filter", "all")  # Default to 'all'

    # Calculate the current date
    current_date = datetime.now()

    # Filter users based on 'last_active_filter'
    if last_active_filter != "all":
        try:
            days_filter = int(last_active_filter)
            all_users = [
                user for user in all_users
                if user.get("last_active")
                   and (current_date - datetime.strptime(user["last_active"], "%Y-%m-%d %H:%M:%S")).days <= days_filter 
            ]
            
        except ValueError:
            logging.error("Invalid last_active_filter value. Showing all users.")

    # Combine user data
    user_data = [
        {
            "primary_email": user.get("primary_email", "N/A"),
            "score": user_scores.get(user.get("primary_email"), {}).get("total_score", 0) if success else 0,
            "last_active": user.get("last_active", "N/A"),
            "contact_numbers": ", ".join(user.get("contact_numbers", [])),
            "active_user": user.get("active_user", False)
        }
        for user in all_users if (user.get("project_id") == session['project_id']) # Display users of this project only
    ]
    logging.info(f"Project suspect Data: {user_data}")
    # Sorting logic
    sort_key = request.args.get("sort", "score")
    order = request.args.get("order", "desc")
    reverse = order == "desc"

    if user_data:
        user_data.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

    return render_template(
        "user_profiles.html",
        user_data=user_data,
        sort_key=sort_key,
        order="asc" if reverse else "desc",
        last_active_filter=last_active_filter  # Pass the active filter to the UI
    )

@app.route('/update_ai_response_state', methods=['POST'])
@login_required
def update_ai_response_state():
    # Extract data from the request
    data = request.get_json()
    thread_id = data.get('thread_id')
    new_state = data.get('new_state')

    # Validate request parameters
    if not thread_id or not new_state:
        logging.error("Thread ID or new state is missing in the request")
        return jsonify({"success": False, "message": "Thread ID and new state are required."}), 400

    logging.info(f"Updating AI response state for thread ID: {thread_id} to {new_state}")

    # Retrieve project details from session information
    session_email = session.get('email')
    if not session_email:
        return jsonify({"success": False, "message": "Session expired or missing email information."}), 401

    # Fetch project details
    project_success, project_details = knowledge_base.get_project_details(session_email)
    if not project_success:
        logging.error(f"Failed to fetch project details for email: {session_email}")
        return jsonify({"success": False, "message": "Failed to fetch project details."}), 500

    # Extract the necessary project details
    project_id = project_details[0]
    app_password = project_details[3]
    admin_prompt = project_details[4]
    response_frequency = project_details[5]
    lower_threshold =  project_details[8],

    # Handle AI response state update logic
    if new_state == "Manual":
        # Switch to manual mode
        logging.info(f"Email structure before switching to automated: {thread_id}, {session_email}, {app_password}, {admin_prompt}")

        success, message = email_processor.switch_to_manual(thread_id)
    elif new_state == "Automated":
        # Switch to automated mode with necessary parameters
        try:
            success, message = email_processor.switch_to_automated(
                project_details=project_details,
                thread_id=thread_id,
                session_email=session_email,
                app_password=app_password,
                response_frequency=response_frequency,
                admin_prompt=admin_prompt,
                lower_threshold=lower_threshold
            )
        except TypeError as e:
            logging.error(f"Error while switching to automated: {e}")
            return jsonify({"success": False, "message": "Failed to update response state due to incorrect data format."}), 500
    else:
        logging.error("Invalid state provided in the request")
        return jsonify({"success": False, "message": "Invalid state provided."}), 400

    # Return the response based on the success of the operation
    if success:
        logging.info(f"Successfully updated AI response state for thread ID: {thread_id} to {new_state}")
        return jsonify({"success": True, "message": "AI response state updated successfully."})
    else:
        logging.error(f"Failed to update AI response state for thread ID: {thread_id}, Reason: {message}")
        return jsonify({"success": False, "message": message}), 500

@app.route('/archive_email', methods=['POST'])
@login_required
def archive_email():
    data = request.get_json()
    thread_id = data.get('key')
    if not thread_id:
        logging.error("Thread ID is missing in the request")
        return jsonify({"success": False, "message": "Thread ID is required."}), 400

    # Mark the email thread as archived
    success, message = email_processor.switch_to_archive(thread_id)

    if success:
        # Use the current project data from a central store instead of a session
        project_data = project_scheduler.process_projects(session_email=session.get('email'),
                                                          session_password=session.get('app_password'))

        if 'conversations' in project_data and thread_id in project_data['conversations']:
            email_list = project_data['conversations'].pop(thread_id)
            project_data['archived_emails'][thread_id] = email_list


        return jsonify({"success": True, "message": "Thread archived successfully."})
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route('/archived_emails')
@login_required
def view_archived_emails():
    # Use process_projects to get the latest project data without relying on session variables
    project_data = project_scheduler.process_projects(session_email=session.get('email'),
                                                      session_password=session.get('app_password'))

    archived_emails = project_data.get('archived_emails', {})
    latest_timestamps = project_data.get('latest_timestamp', {})
    ai_response_state = project_data.get('ai_response_state', {})
    conversations_score = project_data.get('conversations_score', {})
    current_date = datetime.now().date()

    return render_template('archived_emails.html', archived_emails=archived_emails, conversations_score = conversations_score, latest_timestamp=latest_timestamps, ai_response_state = ai_response_state,current_date=current_date)
@app.route('/unarchiving_emails', methods=['POST'])
@login_required
def unarchiving_emails():
    data = request.get_json()
    thread_id = data.get('key')
    email = session['email']

    if not thread_id:
        logging.error("Thread ID is missing in the request")
        return jsonify({"success": False, "message": "Thread ID is required."}), 400

    try:
        success, project_data = knowledge_base.get_project_details(email)
        if not success:
            return jsonify({"success": False, "message": "No project details found for the provided email."}), 404
    except Exception as error:
        logging.error(f"Error fetching project details: {error}")
        return jsonify({"success": False, "message": str(error)}), 500

    # Extract required details from project_data
    prompt = project_data[4]
    response_frequency = project_data[5]

    try:
        # Automatically switch to automated state
        success, message = email_processor.switch_archive_to_automated(
            thread_id=thread_id,
            # session_email=session.get('email'),
            # app_password=session.get('app_password'),
            # response_frequency=response_frequency,
            # admin_prompt=prompt
        )
    except Exception as error:
        logging.error(f"Error switching email thread to Automated: {error}")
        return jsonify({"success": False, "message": str(error)}), 500

    if success:
        # flash(f"Thread {thread_id} has been unarchived and set to Automated.", "success")
        return jsonify({"success": True, "redirect": url_for('index')})
    else:
        return jsonify({"success": False, "message": message}), 500


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
        'end_date': request.args.get('end_date'),
        'top_k_value': request.args.get('top_k_value', type=int)  # New filter to get the top K emails
    }

    # Check session variables for selected project
    if 'email' not in session or 'app_password' not in session:
        # flash("No project selected. Please select a project.", "error")
        return redirect(url_for('all_projects_view'))

    # Get the raw conversation data
    data = project_scheduler.process_projects(filters, session['email'], session['app_password'])
    conversations = data.get('conversations', {})
    conversations_score = data.get('conversations_score', {})
    latest_timestamp = data.get('latest_timestamp', {})
    archived_emails = data.get('archived_emails', {})
    ai_response_state = data.get('ai_response_state', {})
    logging.info(f"ai_response_state: {ai_response_state}")
    session['current_project_archived_emails'] = archived_emails

    # Apply top K filter based on interaction scores
    top_k_value = filters.get('top_k_value')
    if top_k_value is not None and conversations:
        # Flatten the list of conversations to get the first email's score from each thread
        sorted_conversations = sorted(
            conversations.items(),
            key=lambda x: conversations_score.get(x[0], 0) if conversations_score.get(x[0]) is not None else 0,
            reverse=True
        )
        # Take only the top K conversations
        sorted_conversations = sorted_conversations[:top_k_value]

        # Convert sorted list back to dictionary for use in the template
        conversations = dict(sorted_conversations)
    logging.info(f"Session Email: {session.get('email')}")

    # Update data dictionary with the filtered conversations
    data['conversations'] = conversations
    data['latest_timestamp'] = latest_timestamp
    data['ai_response_state'] = ai_response_state
    current_date = datetime.now().date()
    return render_template('index.html', **data, current_date=current_date)


if __name__ == '__main__':
    app.run(debug=True)

