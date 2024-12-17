import logging
from knowledge_base import KnowledgeBase

knowledge_base = KnowledgeBase()

# Configure logging centrally
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Function to drop tables if they exist
def drop_tables(cursor):
    drop_tables_queries = [
        "DROP TABLE IF EXISTS SCORED_EMAILS;",
        "DROP TABLE IF EXISTS EMAIL_THREADS;",
        "DROP TABLE IF EXISTS USER_PROFILES;",
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
            AI_RESPONSE_STATE TEXT NOT NULL DEFAULT 'Automated',
            SEEN_KEYWORDS_DATA JSONB,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS SCORED_EMAILS (
            MESSAGE_ID TEXT PRIMARY KEY,
            THREAD_ID TEXT NOT NULL,
            PROJECT_NAME TEXT,
            LAST_UPDATED TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS USER_PROFILES (
            USER_ID TEXT PRIMARY KEY,
            PRIMARY_EMAIL TEXT,
            PROJECT_ID TEXT,
            THREAD_IDS TEXT,
            EMAIL_LIST TEXT,
            CONTACT_NUMBERS JSON,
            ACTIVE_USER BOOLEAN,
            LAST_ACTIVE TIMESTAMP,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ADMIN_ACCOUNTS (
            ADMIN_ID TEXT PRIMARY KEY,
            PASSWORD TEXT,
            EMAIL_ID TEXT UNIQUE,
            CONTACT_NUMBER TEXT,
            AFFILIATION VARCHAR,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS PROJECTS (
            PROJECT_ID TEXT PRIMARY KEY,
            EMAIL_ID VARCHAR(255) UNIQUE,
            PROJECT_NAME VARCHAR(255) NOT NULL,
            APP_PASSWORD TEXT NOT NULL,
            AI_PROMPT_TEXT TEXT,
            RESPONSE_FREQUENCY INTEGER,
            KEYWORDS_DATA JSONB,
            OWNER_ADMIN_ID TEXT,
            LOWER_THRESHOLD INTEGER,
            UPPER_THRESHOLD INTEGER,
            AUTHORIZED_EMAILS JSONB,
            POSED_NAME VARCHAR(255),
            POSED_AGE INTEGER, -- Age of the young person being posed
            POSED_SEX VARCHAR(10), -- Sex of the young person being posed
            POSED_LOCATION VARCHAR(255), -- Geographical location being posed
            SWITCH_MANUAL_CRITERIAS JSONB,
            LAST_UPDATED TIMESTAMP
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
            logging.error(conn_error)
            exit
        cursor = conn.cursor()

        # Drop existing tables
        drop_tables(cursor)
        logging.info(f"Tables dropped successfully.")

        # Create tables and insert data
        create_tables(cursor)
        logging.info(f"Tables created successfully.")

        # Commit changes
        conn.commit()


    except Exception as e:
        logging.error(f"An error occurred:", e)

    finally:
        cursor.close()
        conn.close()


setup_database()
# success, result = knowledge_base.get_projects_by_admin_email("vamsikinkiri@gmail.com")
# if success:
#     print("Projects found:", result)
# else:
#     print("Error:", result)