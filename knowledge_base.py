import psycopg2
import os
import yaml
import bcrypt
import json
from flask import session


class KnowledgeBase:
   
    def get_db_connection(self):
        """
        Connect to PostgreSQL using credentials stored in 'credentials.yaml'.
        Returns a connection object or None if the connection fails.
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
            return conn, None
        except Exception as error:
            return None, f"Error while connecting to PostgreSQL: {error}"


    def create_admin(self, login_id, password, email_id, phone_number, affiliation):
        """
        Create a new admin in the database.
        """
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error

        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO admin_accounts (login_id, password, email_id, contact_number, affiliation, last_updated)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (login_id, hashed_password, email_id, phone_number, affiliation)
            )
            conn.commit()
            return True, "Account created successfully!"
        except Exception as e:
            return False, f"Error creating account: {e}"
        finally:
            cursor.close()
            conn.close()
    
    def get_password(self, loginId):
        """
        Extract the stored hashed password for the provided login_id.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM admin_accounts WHERE login_id = %s", (loginId,))
            result = cursor.fetchone()
            return True, result

        except Exception as error:
            return False, f"Database error: {error}"

        finally:
            cursor.close()
            conn.close()
    
    def get_app_password(self, email):
        """
        Fetch the app password for a given email from the database.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT app_password FROM projects WHERE email_id = %s", (email,))
            result = cursor.fetchone()
            return True, result
        
        except Exception as error:
            return False, f"Database error: {error}"
        
        finally:
            cursor.close()
            conn.close()

    def create_project(self, email_id, project_name, app_password, prompt_text, response_frequency, keywords_data, assigned_admin_id):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects(email_id, project_name, app_password, prompt_text, response_frequency, keywords_data, assigned_admin_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (email_id, project_name, app_password, prompt_text, response_frequency, keywords_data, assigned_admin_id))
            conn.commit()
            return True, "Project created successfully!"
        except Exception as e:
            return False, f"Error creating project: {e}"
        finally:
            conn.close()
            cursor.close()
    
    def is_email_scored(self, message_id):
        """
        Check if an email is already scored.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM scored_emails WHERE message_id = %s", (message_id,))
            result = cursor.fetchone()
            return True, result is not None
        except Exception as error:
            print(f"Database error while checking scored email: {error}")
            return False, f"Database error while checking scored email: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def update_email_thread(self, thread_id, message_id, score, seen_keywords):
        """
        Insert or update a thread in the email_threads table and record the email in scored_emails.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()

            # Check if thread_id exists
            cursor.execute("""
                SELECT EXISTS (SELECT 1 FROM email_threads WHERE thread_id = %s)
            """, (thread_id,))
            thread_exists = cursor.fetchone()[0]
            if thread_exists:
                # Update existing thread
                cursor.execute("""
                    UPDATE email_threads
                    SET interaction_score = %s,
                        seen_keywords_data = %s,
                        last_updated = NOW()
                    WHERE thread_id = %s
                """, (score, json.dumps(seen_keywords), thread_id))
            else:
                # Insert new thread
                cursor.execute("""
                    INSERT INTO email_threads (
                        thread_id, project_email, project_name, interaction_score,
                        ai_response_enabled, response_frequency, seen_keywords_data,
                        last_updated
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    thread_id,
                    session['email'],  # Project email associated with the thread
                    session['project'],  # Project name associated with the thread
                    score,
                    True,  # AI_RESPONSE_ENABLED set to True
                    0,  # RESPONSE_FREQUENCY initialized to 0
                    json.dumps(seen_keywords)
                ))
            
            # Insert into scored_emails table (always for the current email)
            cursor.execute("""
                INSERT INTO scored_emails (message_id, thread_id, last_updated)
                VALUES (%s, %s, NOW())
            """, (message_id, thread_id))
            conn.commit()
            return True, None
        except Exception as error:
            print(f"Database error while processing email thread: {error}")
            return False, f"Database error while processing email thread: {error}"
        finally:
            cursor.close()
            conn.close()

    
    def get_project_name(self, email):
        """
        Fetch the project name for a given email.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT project_name FROM projects WHERE email_id = %s", (email,))
            result = cursor.fetchone()
            return True, result
        except Exception as error:
            print(f"Database error: {error}")
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_project_keywords(self, email, project_name):
        """
        Fetch the keywords data for a given email and project.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT keywords_data FROM projects 
                WHERE email_id = %s AND project_name = %s
            """, (email, project_name))
            result = cursor.fetchone()
            if result:
                return True, result[0]
            else:
                return True, {}
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_seen_keywords(self, thread_id):
        """
        Fetch the seen keywords for a given thread ID.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT seen_keywords_data FROM email_threads 
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            if result:
                return True, result[0]  # Deserialize JSON data
            else:
                return True, {}
        except Exception as error:
            print(f"Database error: {error}")
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()



