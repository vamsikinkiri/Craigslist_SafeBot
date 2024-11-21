from knowledge_base import KnowledgeBase

knowledge_base = KnowledgeBase()

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
            PRIMARY_EMAIL TEXT PRIMARY KEY,
            THREAD_IDS TEXT,
            EMAIL_LIST TEXT,
            CONTACT_NUMBERS JSON,
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
            email_id VARCHAR(255) NOT NULL PRIMARY KEY,
            project_name VARCHAR(255) NOT NULL,
            app_password TEXT NOT NULL,
            ai_prompt_text TEXT,
            response_frequency INTEGER,
            keywords_data JSONB,
            ASSIGNED_ADMIN_ID BIGINT
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