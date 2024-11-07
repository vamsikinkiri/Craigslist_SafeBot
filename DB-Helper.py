import psycopg2
import bcrypt


# Encrypt password function
def encrypt_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password


# Credentials and connection info
hostname = 'msprojectdatabase.clygcuaekk84.us-west-2.rds.amazonaws.com'
database = 'MsProjectDatabase'  # Your database name
username = 'postgres'
pwd = 'MS_project2024!'
port_id = 5432

# Admin credentials to insert
login_id = '862466036'
password = 'MS_project2024!'

# Encrypt the password
hashed_password = encrypt_password(password).decode('utf-8')  # Convert to string for insertion

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

    # # Create the Admin table if it doesn't exist
    # create_table_query = """
    # CREATE TABLE IF NOT EXISTS admin_accounts (
    #     login_id VARCHAR(20) PRIMARY KEY,
    #     password_hash TEXT NOT NULL
    # );
    # """
    # cursor.execute(create_table_query)
    # conn.commit()

    # Insert the new admin entry if it does not exist
    insert_query = """
    INSERT INTO admin_accounts (login_id, password_hash) VALUES (%s, %s)
    ON CONFLICT (login_id) DO NOTHING;  -- Prevents duplicate inserts if the ID already exists
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
