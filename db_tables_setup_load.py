import hashlib
from datetime import datetime, timedelta
from knowledge_base import KnowledgeBase

knowledge_base = KnowledgeBase()

# def generate_hash(value):
#     return int(hashlib.sha256(value.encode()).hexdigest(), 16) % (10**10)

# Function to create tables if they don't exist
def create_tables(cursor):
    create_tables_queries = [
        """
        CREATE TABLE IF NOT EXISTS EMAIL_THREADS (
            THREAD_ID BIGINT PRIMARY KEY,
            PROJECT_EMAIL TEXT,
            PROJECT_NAME TEXT,
            INTERACTION_SCORE REAL,
            AI_RESPONSE_ENABLED BOOLEAN,
            RESPONSE_FREQUENCY INT,
            seen_keywords_data JSONB,
            ASSIGNED_ADMIN_ID BIGINT,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS SCORED_EMAILS (
            MESSAGE_ID TEXT PRIMARY KEY,
            THREAD_ID TEXT NOT NULL,
            LAST_UPDATED TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS USER_PROFILES (
            USER_ID BIGINT PRIMARY KEY,
            PRIMARY_EMAIL TEXT,
            THREAD_IDS TEXT,
            EMAIL_LIST TEXT,
            CONTACT_NUMBER INT,
            LAST_ACTIVE TIMESTAMP,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ADMIN_ACCOUNTS (
            LOGIN_ID BIGINT PRIMARY KEY,
            PASSWORD TEXT,
            EMAIL_ID TEXT,
            CONTACT_NUMBER INT,
            AFFILIATION VARCHAR,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS PROJECTS (
            email_id VARCHAR(255) NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            app_password TEXT NOT NULL,
            prompt_text TEXT,
            response_frequency INTEGER,
            keywords_data JSONB,
            PRIMARY KEY (email_id, project_name)  -- Composite primary key
        );
        """
    ]
    for query in create_tables_queries:
        cursor.execute(query)


# Main function to set up tables and insert data
def setup_database():
    try:
        # Connect to database
        conn, conn_error = knowledge_base.get_db_connection()
        if conn is None:
            print(conn_error)
            exit
        cursor = conn.cursor()

        # Create tables and insert data
        create_tables(cursor)

        # Commit changes
        conn.commit()
        print("Tables created successfully.")

    except Exception as e:
        print("An error occurred:", e)

    finally:
        cursor.close()
        conn.close()


setup_database()
