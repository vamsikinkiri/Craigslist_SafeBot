import psycopg2
import os
import yaml
import bcrypt
from flask import flash

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

