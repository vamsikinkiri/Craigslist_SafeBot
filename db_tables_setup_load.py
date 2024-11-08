import hashlib
from datetime import datetime, timedelta
from auth_handler import get_db_connection

def generate_hash(value):
    return int(hashlib.sha256(value.encode()).hexdigest(), 16) % (10**10)

# Function to create tables if they don't exist
def create_tables(cursor):
    create_tables_queries = [
        """
        CREATE TABLE IF NOT EXISTS EMAIL_THREADS (
            THREAD_ID BIGINT PRIMARY KEY,
            INTERACTION_SCORE REAL,
            INITIAL_CATEGORY_ID BIGINT,
            FINAL_CATEGORY_ID BIGINT,
            AI_RESPONSE_ENABLED BOOLEAN,
            RESPONSE_FREQUENCY INT,
            ASSIGNED_ADMIN_ID BIGINT,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS USER_PROFILES (
            USER_ID BIGINT PRIMARY KEY,
            THREAD_IDS TEXT,
            EMAIL_LIST TEXT,
            CONTACT_NUMBER INT,
            LAST_ACTIVE TIMESTAMP,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS USER_ACCOUNTS (
            USER_ID BIGINT PRIMARY KEY,
            EMAIL_ID VARCHAR,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ADMIN_ACCOUNTS (
            LOGIN_ID BIGINT PRIMARY KEY,
            PASSWORD_HASH TEXT,
            EMAIL_ID TEXT,
            CONTACT_NUMBER INT,
            AFFILIATION VARCHAR,
            LAST_UPDATED TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS EMAIL_CATEGORIES (
            CATEGORY_ID BIGINT PRIMARY KEY,
            CATEGORY_NAME VARCHAR,
            CRIME_TYPE VARCHAR,
            KEYWORDS_LIST VARCHAR[],
            AI_PROMPT_TEXT VARCHAR,
            LAST_UPDATED TIMESTAMP
        );
        """
    ]
    for query in create_tables_queries:
        cursor.execute(query)


# Insert data into EMAIL_CATEGORIES table
def insert_into_email_categories(cursor):

    CATEGORY_ID = '9189813498137'
    CATEGORY_NAME = 'Burglary'
    CRIME_TYPE = 'Burglary'
    KEYWORDS_LIST = 'Theft, Watches, Premium sales'
    AI_PROMPT_TEXT = ''
    LAST_UPDATED = ''

    # Define insert query
    insert_query = """
        INSERT INTO EMAIL_CATEGORIES (
            CATEGORY_ID, CATEGORY_NAME, CRIME_TYPE, 
            KEYWORDS_LIST, AI_PROMPT_TEXT, LAST_UPDATED
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (CATEGORY_ID) DO NOTHING;
    """

    cursor.execute(insert_query, (
        CATEGORY_ID, CATEGORY_NAME, CRIME_TYPE,
        KEYWORDS_LIST, AI_PROMPT_TEXT, LAST_UPDATED
    ))

# Main function to set up tables and insert data
def setup_database():
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create tables and insert data
        create_tables(cursor)
        insert_into_email_categories(cursor)

        # Commit changes
        conn.commit()
        print("Tables created successfully.")

    except Exception as e:
        print("An error occurred:", e)

    finally:
        cursor.close()
        conn.close()
