import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, login_required
from knowledge_base import KnowledgeBase

# Initialize Flask app and KnowledgeBase instance
app = Flask(__name__)
knowledge_base = KnowledgeBase()

@app.route('/Project_Account_Login', methods=['GET', 'POST'])
def Project_Account_Login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Get a database connection using KnowledgeBase
        conn, conn_error = knowledge_base.get_db_connection()
        if conn is None:
            flash(conn_error, "error")
            return render_template('templates/Project_Account_Login.html')

        cursor = conn.cursor()
        cursor.execute("SELECT app_password FROM projects WHERE email_id = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            stored_password = result[0]
            # Direct password comparison
            if stored_password == password:
                user = UserMixin(id=email)
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password. Please try again.", "error")
        else:
            flash("Email does not exist. Please create an account.", "error")

    return render_template('templates/Project_Account_Login.html')

@app.route('/Project_Creation', methods=['GET', 'POST'])
@login_required
def Project_Creation():
    if request.method == 'POST':
        email = request.form['email']
        project_name = request.form['project_name']
        app_password = request.form['password']
        prompt_text = request.form.get('prompt_text', '')
        response_frequency = int(request.form.get('response_frequency', 0))

        # Get keywords data and convert it to JSON format
        keywords_data = json.loads(request.form['keywords_data'])
        keywords_json = json.dumps(keywords_data)

        # Get a database connection using KnowledgeBase
        conn, conn_error = knowledge_base.get_db_connection()
        if conn is None:
            flash(conn_error, "error")
            return render_template('templates/Project_Creation.html')

        cursor = conn.cursor()
        cursor.execute('''INSERT INTO projects (email_id, project_name, app_password, prompt_text, response_frequency, keywords_data) 
                          VALUES (%s, %s, %s, %s, %s, %s)''',
                       (email, project_name, app_password, prompt_text, response_frequency, keywords_json))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Project created successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('templates/Project_Creation.html')

# Define a dashboard route for testing login
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')
