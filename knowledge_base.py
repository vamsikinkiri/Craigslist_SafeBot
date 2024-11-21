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
                INSERT INTO projects(email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, assigned_admin_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (email_id, project_name, app_password, prompt_text, response_frequency, keywords_data, assigned_admin_id))
            conn.commit()
            return True, "Project created successfully!"
        except Exception as e:
            return False, f"Error creating project: {e}"
        finally:
            conn.close()
            cursor.close()
    
    def is_email_processed(self, message_id):
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
    
    def get_interaction_score(self, thread_id):
        """
        Retrieve the INTERACTION_SCORE value for a given thread from the EMAIL_THREADS table.
        Args: thread_id (str): The thread ID.
        Returns: tuple: (bool, float) Success status and the INTERACTION_SCORE value or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT interaction_score FROM email_threads
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            return True, result
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()

    def fetch_all_email_threads(self):
        conn, conn_error = self.get_db_connection()
        if conn is None:
            raise Exception(conn_error)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    et.thread_id,
                    et.interaction_score
                FROM email_threads et
                JOIN scored_emails se ON et.thread_id = se.thread_id
            """)
            rows = cursor.fetchall()
            email_threads = []
            for row in rows:
                email_threads.append({
                    "thread_id": row[0],
                    "interaction_score": row[1]
                })

            return email_threads

        except Exception as error:
            print(f"Database error while fetching email threads: {error}")
            raise
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
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_user_profile(self, user_email):
        """
        Retrieve user profile by email.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            print(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM USER_PROFILES WHERE PRIMARY_EMAIL = %s
            """, (user_email,))
            result = cursor.fetchone()
            return True, result
        except Exception as error:
            print(f"Database error while retrieving user profile: {error}")
            return False, f"Database error while retrieving user profile: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def update_user_profile(self, user_email, thread_ids, contact_numbers, last_active):
        """
        Update THREAD_IDS and LAST_UPDATED for a user.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            print(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE USER_PROFILES
                SET THREAD_IDS = %s, CONTACT_NUMBERS = %s, LAST_ACTIVE = %s, LAST_UPDATED = NOW()
                WHERE PRIMARY_EMAIL = %s
            """, (json.dumps(thread_ids), json.dumps(contact_numbers), last_active, user_email))
            conn.commit()
            return True, None
        except Exception as error:
            print(f"Database error while updating user profile: {error}")
            return False, f"Database error while updating user profile: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def create_user_profile(self, user_email, thread_ids, email_list, contact_numbers, last_active):
        """
        Create a new user profile.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            print(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO USER_PROFILES (
                    PRIMARY_EMAIL, THREAD_IDS, EMAIL_LIST, CONTACT_NUMBERS, 
                    LAST_ACTIVE, LAST_UPDATED
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (
                user_email, json.dumps(thread_ids), email_list, json.dumps(contact_numbers), last_active
            ))
            conn.commit()
            return True, None
        except Exception as error:
            print(f"Database error while creating user profile: {error}")
            return False, f"Database error while creating user profile: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_ai_prompt_text(self, email_id, project_name):
        """
        Retrieve the prompt_text for a given project from the PROJECTS table.

        Args:
            email_id (str): The email ID associated with the project.
            project_name (str): The name of the project.

        Returns:
            tuple: (bool, str) Success status and the prompt text or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ai_prompt_text FROM projects
                WHERE email_id = %s AND project_name = %s
            """, (email_id, project_name))
            result = cursor.fetchone()
            return True, result
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()

    def get_ai_response_enabled(self, thread_id):
        """
        Retrieve the AI_RESPONSE_ENABLED value for a given thread from the EMAIL_THREADS table.
        Args: thread_id (str): The thread ID.
        Returns: tuple: (bool, bool) Success status and the AI_RESPONSE_ENABLED value or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ai_response_enabled FROM email_threads
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            print(result)
            return True, result
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()

    def update_ai_response_enabled(self, thread_id, new_value):
        """
        Update the AI_RESPONSE_ENABLED value for a given thread in the EMAIL_THREADS table.

        Args:
            thread_id (str): The thread ID.
            new_value (bool): The new value for AI_RESPONSE_ENABLED.

        Returns: tuple: (bool, str) Success status and a success or error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_threads
                SET ai_response_enabled = %s, last_updated = NOW()
                WHERE thread_id = %s
            """, (new_value, thread_id))
            conn.commit()
            return True, "AI_RESPONSE_ENABLED updated successfully."
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_response_frequency(self, thread_id):
        """
        Retrieve the RESPONSE_FREQUENCY value for a given thread from the EMAIL_THREADS table.
        Args: thread_id (str): The thread ID.
        Returns: tuple: (bool, int) Success status and the RESPONSE_FREQUENCY value or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT response_frequency FROM email_threads
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            return True, result # Use result[0]
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()


    def get_project_details(self, email, project_name):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT prompt_text, response_frequency
                FROM projects
                WHERE email_id = %s AND project_name = %s
                """,
                (email, project_name)
            )
            result = cursor.fetchone()

            if not result:
                return False, "No project found for the given email and project name."
            project_details = {
                "prompt_text": result[0],
                "response_frequency": result[1]
            }
            return True, project_details
        except Exception as e:
            return False, f"Error fetching project details: {e}"
        finally:
            cursor.close()
            conn.close()

    def update_project(self,email, project_name, prompt_text, response_frequency):
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects SET prompt_text = %s, response_frequency = %s
                WHERE email_id = %s AND project_name = %s
            """, (prompt_text, response_frequency, email, project_name))

            if cursor.rowcount == 0:
                return False, "No matching project found for the provided email and project name."
            conn.commit()
            return True, "Project details updated successfully."
        except Exception as error:
            print(f"Database error: {error}")
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()

    def get_account_profile(self, login_id):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT login_id, contact_number, affiliation, email_id, last_updated
                FROM admin_accounts
                WHERE login_id = %s
                """,
                (login_id,)
            )
            print(login_id)
            record = cursor.fetchone()
            if not record:
                return False, f"No account found for login_id: {login_id}."
            account_profile = {
                "login_id": record[0],
                "phone_number": record[1],
                "affiliation": record[2],
                "email_id": record[3],
                "last_updated": record[4]
            }
            print(f"Fetching account profile for Login ID: {login_id}")
            return True, account_profile
        except Exception as e:
            return False, f"Error fetching account profile: {e}"
        finally:
            cursor.close()
            conn.close()

    def update_account_profile(self, login_id, phone_number, affiliation, email_id):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE admin_accounts
                SET contact_number = %s,
                    affiliation = %s,
                    email_id = %s,
                    last_updated = NOW()
                WHERE login_id = %s
                """,
                (phone_number, affiliation, email_id, login_id)
            )
            conn.commit()
            print(f"Executing query: UPDATE admin_accounts SET contact_number = {phone_number}, affiliation = {affiliation}, email_id = {email_id} WHERE login_id = {login_id}")
            if cursor.rowcount == 0:
                cursor.execute(""" SELECT 1 FROM admin_accounts WHERE login_id = %s AND contact_number = %s AND affiliation = %s AND email_id = %s """, (login_id, phone_number, affiliation, email_id) )
                if cursor.fetchone():
                    return True, "No changes were made; profile already up-to-date."
                return False, "No account found with the provided login_id."
            return True, "Profile updated successfully!"
        except Exception as e:
            return False, f"Error updating profile: {e}"
        finally:
            cursor.close()
            conn.close()






