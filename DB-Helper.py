import psycopg2
import bcrypt


# Encrypt password function
def encrypt_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password


# Credentials and connection info
hostname = 'localhost'
database = 'postgres'#'MsProjectDatabase'  # Your database name
username = 'postgres'
pwd = 'MS_project2024'
port_id = 5432

# Admin credentials to insert
login_id = '862466036'
password = '' ##Password 

# Encrypt the password
hashed_password = encrypt_password(password).decode('utf-8')  # Convert to string for insertion

# SQL queries to create tables if they do not exist
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
        EVENT_DATE DATE,
        REPORT_DATE DATE,
        KEYWORDS_LIST VARCHAR[],
        AI_PROMPT_TEXT VARCHAR,
        LAST_UPDATED TIMESTAMP
    );
    """
]

try:
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        host=hostname,
        dbname=database,
        user=username,
        password=pwd,
        port=port_id
    )

    # Create a cursor object
    cursor = conn.cursor()

    # Execute each table creation query
    for query in create_tables_queries:
        cursor.execute(query)
    conn.commit()
    print("Tables created successfully!")

    # Insert the new admin entry if it does not exist
    insert_query = """
    INSERT INTO admin_accounts (login_id, password_hash) VALUES (%s, %s)
    ON CONFLICT (login_id) DO NOTHING;
    """

    # Execute the query with the login_id and hashed password
    cursor.execute(insert_query, (login_id, hashed_password))
    conn.commit()

    print("Admin entry inserted successfully!")

    # Close communication with the database
    cursor.close()
    conn.close()

except Exception as error:
    print("Error while inserting into PostgreSQL:", error)
