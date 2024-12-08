import psycopg2
import os
import yaml
import bcrypt
import json
import random
import string
import logging
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
    

    def generate_random_string(self, length=10):
        """
        Generate a random string of the specified length.
        Args: length (int): The length of the random string.
        Returns: str: A randomly generated string.
        """
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))
    

    def is_generated_id_unique(self, db_table, col_name, generated_id):
        """
        Check if the given login ID is unique in the database.
        Args:
            generated_id (str): The login ID to check.
            db_table (str): Which table to check for uniqueness
            col_name (str): Which column in the table to check
        Returns:
            bool: True if unique, False otherwise.
        """
        conn, conn_error = self.get_db_connection()
        if not conn:
            return conn_error

        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT 1 FROM {db_table} WHERE {col_name} = %s", (generated_id,))
            return cursor.fetchone() is None
        except Exception as e:
            logging.error(f"Database error while checking login ID uniqueness: {e}")
            return False
        finally:
            cursor.close()
            conn.close()


    def create_admin(self, password, email_id, phone_number, affiliation):
        """
        Create a new admin in the database.
        """
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error

        cursor = conn.cursor()
        generated_id = self.generate_random_string(10)
        while not self.is_generated_id_unique(db_table="admin_accounts", col_name="admin_id", generated_id=generated_id):
            generated_id = self.generate_random_string(10)

        try:
            cursor.execute(
                """
                INSERT INTO admin_accounts (admin_id, password, email_id, contact_number, affiliation, last_updated)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (generated_id, hashed_password, email_id, phone_number, affiliation)
            )
            conn.commit()
            return True, "Account created successfully!"
        except Exception as e:
            return False, f"Error creating account: {e}"
        finally:
            cursor.close()
            conn.close()

    def get_admin_details(self, email_id):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT admin_id, password, contact_number, affiliation, email_id, last_updated
                FROM admin_accounts
                WHERE EMAIL_ID = %s
                """,
                (email_id,)
            )
            result = cursor.fetchone()
            if not result:
                return False, f"No account found for Email ID: {email_id}."
            account_profile = {
                "admin_id": result[0],
                "password": result[1],
                "phone_number": result[2],
                "affiliation": result[3],
                "email_id": result[4],
                "last_updated": result[5]
            }
            return True, account_profile
        except Exception as e:
            return False, f"Error fetching account profile: {e}"
        finally:
            cursor.close()
            conn.close()
    
    def get_email_by_admin_id(self, admin_id):
        """
        Fetch the email ID associated with a given admin ID from the ADMIN_ACCOUNTS table.
        Args: admin_id (str): The admin ID to search for.
        Returns: tuple: (bool, str): Success status and the email ID or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""SELECT EMAIL_ID FROM ADMIN_ACCOUNTS WHERE ADMIN_ID = %s""", (admin_id,))
            result = cursor.fetchone()

            if result:
                return True, result[0]  # Return the email ID
            else:
                return False, f"No email ID found for admin ID: {admin_id}"
        except Exception as e:
            logging.error(f"Database error while retrieving email by admin ID: {e}")
            return False, f"Database error: {e}"
        finally:
            cursor.close()
            conn.close()

    
    def update_admin_profile(self, admin_id, phone_number, affiliation, email_id):
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
                WHERE admin_id = %s
                """,
                (phone_number, affiliation, email_id, admin_id)
            )
            conn.commit()
            logging.info(f"Executing query: UPDATE admin_accounts SET contact_number = {phone_number}, affiliation = {affiliation}, email_id = {email_id} WHERE admin_id = {admin_id}")
            if cursor.rowcount == 0:
                cursor.execute(""" SELECT 1 FROM admin_accounts WHERE admin_id = %s AND contact_number = %s AND affiliation = %s AND email_id = %s """, (admin_id, phone_number, affiliation, email_id) )
                if cursor.fetchone():
                    return True, "No changes were made; profile already up-to-date."
                return False, "No account found with the provided admin_id."
            return True, "Profile updated successfully!"
        except Exception as e:
            return False, f"Error updating profile: {e}"
        finally:
            cursor.close()
            conn.close()

    def create_project(self, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, lower_threshold, upper_threshold, authorized_emails, last_updated):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error
        
        generated_id = self.generate_random_string(12)
        while not self.is_generated_id_unique(db_table="projects", col_name="project_id", generated_id=generated_id):
            generated_id = self.generate_random_string(10)

        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO projects(
                project_id, email_id, project_name, app_password, ai_prompt_text, 
                response_frequency, keywords_data, owner_admin_id, lower_threshold, 
                upper_threshold, authorized_emails, last_updated) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s::jsonb, NOW())
                ''', 
                (generated_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, lower_threshold, upper_threshold, json.dumps(authorized_emails)))
            conn.commit()
            return True, "Project created successfully!"
        except Exception as e:
            logging.error(f"Error creating project: {e}")
            return False, f"Error creating project: {e}"
        finally:
            conn.close()
            cursor.close()
    
    def is_email_unique_in_projects(self, email_id):
        """
        Check if the provided email ID already exists in the projects table.
        Args: email_id (str): The email ID to check.
        Returns: tuple: (bool, str): Success status and a message indicating presence or error.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""SELECT 1 FROM projects WHERE email_id = %s""", (email_id,))
            result = cursor.fetchone()

            if result:
                return False, "Email ID already exists for a project. Try again!"
            else:
                return True, None
        except Exception as e:
            logging.error(f"Database error while checking email ID presence: {e}")
            return False, f"Database error: {e}"
        finally:
            cursor.close()
            conn.close()

    def get_project_details(self, email_id):
        """
        Retrieve project details by email.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM PROJECTS WHERE EMAIL_ID = %s
            """, (email_id,))
            result = cursor.fetchone()
            return True, result
        except Exception as error:
            logging.error(f"Database error while retrieving project details: {error}")
            return False, f"Database error while retrieving project details: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_project_details_by_id(self, project_id):
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error
        try:
            cursor = conn.cursor()
            # SQL Query to get the project details by ID
            query = """
                SELECT * FROM projects WHERE project_id = %s
            """
            cursor.execute(query, (project_id,))
            project_details = cursor.fetchone()

            if not project_details:
                return False, "Project not found."

            return True, project_details

        except Exception as e:
            logging.error(f"Error fetching project details by ID: {e}")
            return False, str(e)

        finally:
            cursor.close()
            if conn:
                conn.close()


    def fetch_all_projects(self):
        """
        Fetch all projects and their details from the database.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, lower_threshold, upper_threshold, authorized_emails, date(last_updated) as Last_Updated FROM projects")
            projects = cursor.fetchall()
            return True, projects
        except Exception as error:
            return False, f"Database error while fetching all projects: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_projects_by_admin_email(self, admin_email):
        """
        Retrieve all projects where the given admin email is present in the authorized_emails field.
        Parameters: admin_email (str): The email ID of the admin to search for in authorized_emails.
        Returns: tuple: (success (bool), result (list of project details or error message))
        """
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error

        try:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM projects
                WHERE authorized_emails @> %s::jsonb
            '''
            cursor.execute(query, [json.dumps([admin_email])])
            projects = cursor.fetchall()

            if projects:
                # Convert the query results to a list of dictionaries for better readability
                result = [
                    {
                        "project_id": project[0],
                        "project_email": project[1],
                        "project_name": project[2],
                        "app_password": project[3],
                        "ai_prompt_text": project[4],
                        "response_frequency": project[5],
                        "keywords_data": project[6],
                        "owner_admin_id": project[7],
                        "lower_threshold": project[8],
                        "upper_threshold": project[9],
                        "authorized_emails": project[10],
                        "last_updated": project[11]
                    }
                    for project in projects
                ]
                return True, result
            else:
                return False, "No projects found for the given admin email."

        except Exception as e:
            logging.error(f"Error retrieving projects for admin email {admin_email}: {e}")
            return False, f"Error retrieving projects: {e}"

        finally:
            conn.close()
            cursor.close()
    def update_project(self, email, project_name, ai_prompt_text, response_frequency, keywords_data, lower_threshold, upper_threshold, authorized_emails):
        # Get database connection
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        cursor = None
        try:
            cursor = conn.cursor()

            logging.info(f"Executing update query with email={email}, project_name={project_name}, "
                         f"ai_prompt_text={ai_prompt_text}, response_frequency={response_frequency}, "
                         f"keywords_data={keywords_data}, lower_threshold={lower_threshold}, "
                         f"upper_threshold={upper_threshold}, authorized_emails={authorized_emails}")

            # Update the project details in the database
            cursor.execute("""
                UPDATE projects
                SET ai_prompt_text = %s,
                    response_frequency = %s,
                    keywords_data = %s,
                    lower_threshold = %s,
                    upper_threshold = %s,
                    authorized_emails = %s::jsonb,
                    last_updated = NOW()
                WHERE email_id = %s AND project_name = %s
            """, (ai_prompt_text, response_frequency, keywords_data, lower_threshold, upper_threshold, json.dumps(authorized_emails), email, project_name))

            if cursor.rowcount == 0:
                logging.warning(f"No matching project found for email={email} and project_name={project_name}.")
                return False, "No matching project found for the provided email and project name."

            # Commit changes to the database
            conn.commit()
            logging.info(f"Project details updated successfully for email={email}, project_name={project_name}.")
            return True, "Project details updated successfully."

        except Exception as error:
            logging.error(f"Database error while updating project: {error}")
            return False, f"Database error: {error}"

        finally:
            # Close cursor and connection if they were successfully created
            if cursor:
                cursor.close()
            if conn:
                conn.close()


    # def update_project(self, email, project_name, ai_prompt_text, response_frequency):
    #     # Get database connection
    #     conn, conn_error = self.get_db_connection()
    #     if conn is None:
    #         return False, conn_error
    #
    #     cursor = None
    #     try:
    #         cursor = conn.cursor()
    #
    #         logging.info(f"Executing update query with email={email}, project_name={project_name}, "
    #                      f"ai_prompt_text={ai_prompt_text}, response_frequency={response_frequency}")
    #
    #         # Update the project details in the database
    #         cursor.execute("""
    #             UPDATE projects SET ai_prompt_text = %s, response_frequency = %s
    #             WHERE email_id = %s AND project_name = %s
    #         """, (ai_prompt_text, response_frequency, email, project_name))
    #
    #         if cursor.rowcount == 0:
    #             logging.warning(f"No matching project found for email={email} and project_name={project_name}.")
    #             return False, "No matching project found for the provided email and project name."
    #
    #         # Commit changes to the database
    #         conn.commit()
    #         logging.info(f"Project details updated successfully for email={email}, project_name={project_name}.")
    #         return True, "Project details updated successfully."
    #
    #     except Exception as error:
    #         logging.error(f"Database error while updating project: {error}")
    #         return False, f"Database error: {error}"
    #
    #     finally:
    #         # Close cursor and connection if they were successfully created
    #         if cursor:
    #             cursor.close()
    #         if conn:
    #             conn.close()
    
    def delete_project(self, project_id):
        try:
            # Get the database connection
            conn, conn_error = self.get_db_connection()
            if not conn:
                return False, conn_error

            cursor = conn.cursor()

            # SQL Query to delete the project by ID
            delete_query = """
                DELETE FROM projects
                WHERE project_id = %s
            """
            cursor.execute(delete_query, (project_id,))
            conn.commit()

            # Check if any row was deleted
            if cursor.rowcount == 0:
                return False, "Project not found or could not be deleted."
            return True, "Project deleted successfully."
        except Exception as e:
            logging.error(f"Error deleting project: {e}")
            return False, str(e)

        finally:
            cursor.close()
            if conn:
                conn.close()

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
            logging.error(f"Database error while checking scored email: {error}")
            return False, f"Database error while checking scored email: {error}"
        finally:
            cursor.close()
            conn.close()

    def update_email_thread(self, thread_id, session_email, session_project, message_id, score, seen_keywords):
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
                        ai_response_state, seen_keywords_data,
                        last_updated
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    thread_id,
                    session_email,  # Project email associated with the thread
                    session_project,  # Project name associated with the thread
                    score,
                    'Automated',  # AI_RESPONSE_STATE set to automated
                    json.dumps(seen_keywords)
                ))

            # Insert into scored_emails table (always for the current email)
            cursor.execute("""
                INSERT INTO scored_emails (message_id, thread_id, project_name, last_updated)
                VALUES (%s, %s, %s, NOW())
            """, (message_id, thread_id, session_project))
            conn.commit()
            return True, None
        except Exception as error:
            logging.error(f"Database error while processing email thread: {error}")
            return False, f"Database error while processing email thread: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def update_email_score(self, thread_id, score):
        """
        Update a thread score in the email_threads table.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()            
            # Update existing thread
            cursor.execute("""
                UPDATE email_threads
                SET interaction_score = %s,
                    last_updated = NOW()
                WHERE thread_id = %s
            """, (score, thread_id))
            conn.commit()
            return True, None
        except Exception as error:
            logging.error(f"Database error while updating email thread: {error}")
            return False, f"Database error while updating email thread: {error}"
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

    def fetch_all_archived_emails(self, project_email):
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            # Fetch archived emails for the specified project email
            project_email_clean = project_email.strip().lower() if project_email else None
            logging.info(f"Fetching archived emails for project email: {project_email_clean}")

            cursor.execute("""
                SELECT thread_id, project_email, project_name, interaction_score, ai_response_state, seen_keywords_data, last_updated
                FROM email_threads
                WHERE lower(ai_response_state) like '%archive%'
                AND lower(project_email) = %s
            """, (project_email_clean,))

            rows = cursor.fetchall()

            # Check if no rows are returned
            if not rows:
                logging.warning(f"No archived emails found for project email: {project_email_clean}")
                return True, {}

            archived_emails = {}
            for row in rows:
                # Ensure the row has the expected length
                if len(row) != 7:
                    logging.error(f"Unexpected tuple length: {len(row)}, expected 7. Tuple: {row}")
                    continue

                thread_id = row[0]
                if thread_id not in archived_emails:
                    archived_emails[thread_id] = []
                archived_emails[thread_id].append({
                    "thread_id": row[0],
                    "project_email": row[1],
                    "project_name": row[2],
                    "interaction_score": row[3],
                    "ai_response_state": row[4],
                    "seen_keywords_data": row[5],
                    "last_updated": row[6]
                })

            return True, archived_emails

        except Exception as error:
            logging.error(f"Database error while fetching archived emails: {error}")
            return False, f"Database error: {error}"

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


    def fetch_top_k_threads(self, k_value):
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            # Fetch the top K threads based on their interaction score
            cursor.execute("""
                SELECT thread_id, project_email, project_name, interaction_score, ai_response_state, seen_keywords_data, last_updated
                FROM email_threads
                ORDER BY interaction_score DESC
                LIMIT %s
            """, (k_value,))

            threads = []
            for row in cursor.fetchall():
                threads.append({
                    "thread_id": row[0],
                    "project_email": row[1],
                    "project_name": row[2],
                    "interaction_score": row[3],
                    "ai_response_state": row[4],
                    "seen_keywords_data": row[5],
                    "last_updated": row[6]
                })

            return True, threads

        except Exception as error:
            logging.error(f"Database error while fetching top K threads: {error}")
            return False, f"Database error: {error}"
        finally:
            if cursor:
                cursor.close()
            if conn:
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
            logging.error(f"Database error while fetching email threads: {error}")
            raise
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
    
    def create_user_profile(self, user_email, thread_ids, email_list, contact_numbers, active_user, last_active):
        """
        Create a new user profile.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error
        
        generated_id = self.generate_random_string(8)
        while not self.is_generated_id_unique(db_table="USER_PROFILES", col_name="USER_ID", generated_id=generated_id):
            generated_id = self.generate_random_string(10)

        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO USER_PROFILES (
                    USER_ID, PRIMARY_EMAIL, THREAD_IDS, EMAIL_LIST, CONTACT_NUMBERS, 
                    ACTIVE_USER, LAST_ACTIVE, LAST_UPDATED
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                generated_id, user_email, thread_ids, email_list, json.dumps(contact_numbers), active_user, last_active
            ))
            conn.commit()
            return True, None
        except Exception as error:
            logging.error(f"Database error while creating user profile: {error}")
            return False, f"Database error while creating user profile: {error}"
        finally:
            cursor.close()
            conn.close()

    def get_user_profile(self, user_email):
        """
        Retrieve user profile by email.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM USER_PROFILES WHERE PRIMARY_EMAIL = %s
            """, (user_email,))
            result = cursor.fetchone()
            return True, result
        except Exception as error:
            logging.error(f"Database error while retrieving user profile: {error}")
            return False, f"Database error while retrieving user profile: {error}"
        finally:
            cursor.close()
            conn.close()
    

    def get_all_user_profiles(self):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error
        cursor = conn.cursor()
        try:
            # Query to fetch all user profiles
            query = """
            SELECT
                USER_ID, 
                PRIMARY_EMAIL, 
                THREAD_IDS, 
                EMAIL_LIST, 
                CONTACT_NUMBERS,
                ACTIVE_USER, 
                LAST_ACTIVE, 
                LAST_UPDATED
            FROM 
                USER_PROFILES
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                return False, "No user profiles found."

            user_profiles = []
            for row in rows:
                user_id, primary_email, thread_ids, email_list, contact_numbers, active_user, last_active, last_updated = row

                # Parse THREAD_IDS as a list if it's a JSON-like string
                parsed_thread_ids = json.loads(thread_ids) if thread_ids and thread_ids.startswith('[') else thread_ids.split(',') if thread_ids else []

                # Parse CONTACT_NUMBERS safely
                parsed_contact_numbers = json.loads(contact_numbers) if isinstance(contact_numbers, str) else contact_numbers

                # Can include the logic to only send the active users using the active_user field
                user_profiles.append({
                    "user_id": user_id,
                    "primary_email": primary_email,
                    "thread_ids": parsed_thread_ids,
                    "email_list": email_list if email_list else "",
                    "contact_numbers": parsed_contact_numbers if parsed_contact_numbers else [],
                    "active_user": active_user,
                    "last_active": last_active.strftime('%Y-%m-%d %H:%M:%S') if last_active else "Never",
                    "last_updated": last_updated.strftime('%Y-%m-%d %H:%M:%S') if last_updated else "Never"
                })
            return True, user_profiles
        except Exception as e:
            return False, f"Error fetching user profiles: {e}"
        finally:
            cursor.close()
            conn.close()
    
    def update_user_profile(self, user_email, thread_ids, contact_numbers, active_user, last_active):
        """
        Update THREAD_IDS and LAST_UPDATED for a user.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE USER_PROFILES
                SET THREAD_IDS = %s, CONTACT_NUMBERS = %s, ACTIVE_USER = %s, LAST_ACTIVE = %s, LAST_UPDATED = NOW()
                WHERE PRIMARY_EMAIL = %s
            """, (thread_ids, json.dumps(contact_numbers), active_user, last_active, user_email))
            conn.commit()
            return True, None
        except Exception as error:
            logging.error(f"Database error while updating user profile: {error}")
            return False, f"Database error while updating user profile: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def get_user_last_active(self, user_email):
        """
        Retrieve user profile by email.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT LAST_ACTIVE FROM USER_PROFILES WHERE PRIMARY_EMAIL = %s
            """, (user_email,))
            result = cursor.fetchone()
            return True, result[0]
        except Exception as error:
            logging.error(f"Database error while retrieving user's last active time: {error}")
            return False, f"Database error while retrieving user's last active time: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def update_active_user(self, user_email, active_user):
        """
        Update THREAD_IDS and LAST_UPDATED for a user.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            logging.error(conn_error)
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE USER_PROFILES
                SET ACTIVE_USER = %s, LAST_UPDATED = NOW()
                WHERE PRIMARY_EMAIL = %s
            """, (active_user, user_email))
            conn.commit()
            return True, None
        except Exception as error:
            logging.error(f"Database error while updating active user: {error}")
            return False, f"Database error while updating active user: {error}"
        finally:
            cursor.close()
            conn.close()

    def get_ai_response_state(self, thread_id):
        """
        Retrieve the AI_RESPONSE_STATE value for a given thread from the EMAIL_THREADS table.
        Args: thread_id (str): The thread ID.
        Returns: tuple: (bool, str): Success status and the AI response state or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""SELECT AI_RESPONSE_STATE FROM EMAIL_THREADS WHERE THREAD_ID = %s""", (thread_id,))
            result = cursor.fetchone()
            if result:
                return True, result[0]
            else:
                return False, "No state found for the given thread ID."
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()

    def update_ai_response_state(self, thread_id, new_state):
        """
        Update the AI_RESPONSE_STATE value for a given thread in the EMAIL_THREADS table.
        Args:
            thread_id (str): The thread ID.
            new_state (str): The new state ('Manual', 'Automated', 'Archive').
        Returns: tuple: (bool, str): Success status and a success or error message.
        """
        valid_states = ['Manual', 'Automated', 'Archive']
        if new_state not in valid_states:
            return False, f"Invalid state: {new_state}. Must be one of {valid_states}."

        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE EMAIL_THREADS
                SET AI_RESPONSE_STATE = %s, LAST_UPDATED = NOW()
                WHERE THREAD_ID = %s
            """, (new_state, thread_id))
            conn.commit()
            if cursor.rowcount > 0:
                return True, "AI response state updated successfully."
            else:
                return False, "No thread found with the given thread ID."
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()

    
    def get_response_frequency(self, email):
        """
        Retrieve the RESPONSE_FREQUENCY value for a given project from the projects table.
        Args: email (str): The project email.
        Returns: tuple: (bool, int) Success status and the RESPONSE_FREQUENCY value or an error message.
        """
        conn, conn_error = self.get_db_connection()
        if conn is None:
            return False, conn_error

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT response_frequency FROM projects
                WHERE email_id = %s
            """, (email,))
            result = cursor.fetchone()
            return True, result # Use result[0]
        except Exception as error:
            return False, f"Database error: {error}"
        finally:
            cursor.close()
            conn.close()
    
    def fetch_scores_at_user_level(self):
        conn, conn_error = self.get_db_connection()
        if not conn:
            return False, conn_error

        cursor = conn.cursor()
        try:
            # Corrected SQL Query
            query = """
                SELECT 
                    up.primary_email AS user_email,
                    et.thread_id AS thread_ids,
                    et.interaction_score AS user_scores
                FROM 
                    email_threads et
                JOIN 
                    user_profiles up 
                ON 
                    et.thread_id = regexp_replace(up.thread_ids, '[\\[\\]\"]', '', 'g')
                ORDER BY 
                    et.interaction_score DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                return False, "No user scores found."

            # Build the user_scores dictionary
            user_scores = {}
            for user_email, thread_id, score in rows:
                if user_email not in user_scores:
                    user_scores[user_email] = {"total_score": 0}
                user_scores[user_email]["total_score"] += score

            logging.info(f"DEBUG DB: Scores Data: {user_scores}")  # Debugging
            return True, user_scores

        except Exception as e:
            return False, f"Error fetching user scores: {e}"
        finally:
            cursor.close()
            conn.close()
