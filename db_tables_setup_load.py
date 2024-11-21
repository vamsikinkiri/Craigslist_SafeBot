import hashlib
from datetime import datetime, timedelta
from knowledge_base import KnowledgeBase

knowledge_base = KnowledgeBase()

# Function to drop tables if they exist
def drop_tables(cursor):
    drop_tables_queries = [
        "DROP TABLE IF EXISTS SCORED_EMAILS;",
        "DROP TABLE IF EXISTS EMAIL_THREADS;",
        "DROP TABLE IF EXISTS USER_PROFILES;"
        # "DROP TABLE IF EXISTS ADMIN_ACCOUNTS;",
        # "DROP TABLE IF EXISTS PROJECTS;"
    ]
    for query in drop_tables_queries:
        cursor.execute(query)

# Function to create tables if they don't exist
def create_tables(cursor):
    create_tables_queries = [
        """
        CREATE TABLE IF NOT EXISTS EMAIL_THREADS (
            THREAD_ID TEXT PRIMARY KEY,
            PROJECT_EMAIL TEXT,
            PROJECT_NAME TEXT,
            INTERACTION_SCORE REAL,
            AI_RESPONSE_ENABLED BOOLEAN,
            RESPONSE_FREQUENCY INT,
            SEEN_KEYWORDS_DATA JSONB,
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
            CONTACT_NUMBER TEXT,
            AFFILIATION VARCHAR,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS PROJECTS (
            EMAIL_ID VARCHAR(255) NOT NULL,
            PROJECT_NAME VARCHAR(255) NOT NULL,
            APP_PASSWORD TEXT NOT NULL,
            PROMPT_TEXT TEXT,
            RESPONSE_FREQUENCY INTEGER,
            KEYWORDS_DATA JSONB,
            ASSIGNED_ADMIN_ID BIGINT,
            PRIMARY KEY (EMAIL_ID, PROJECT_NAME)  -- COMPOSITE PRIMARY KEY
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

        # Drop existing tables
        drop_tables(cursor)
        print("Tables dropped successfully.")

        # Create tables and insert data
        create_tables(cursor)
        print("Tables created successfully.")

        # Commit changes
        conn.commit()


    except Exception as e:
        print("An error occurred:", e)

    finally:
        cursor.close()
        conn.close()


setup_database()