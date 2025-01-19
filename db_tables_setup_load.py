import logging
import json
from string import Template
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
         "DROP TABLE IF EXISTS PROJECTS;"
         "DROP TABLE IF EXISTS PROJECT_TYPES;"
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
        CREATE TABLE IF NOT EXISTS PROJECT_TYPES (
            PROJECT_TYPE TEXT PRIMARY KEY UNIQUE,
            PROJECT_TYPE_ID TEXT UNIQUE,
            DEFAULT_ADMIN_PROMPT TEXT,
            BASE_PROMPT TEXT,
            SCENARIO_PROMPT TEXT,
            RESPONSE_PROMPT TEXT,
            DEFAULT_SWITCH_MANUAL_CRITERIAS JSONB, 
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
            ACTION_REMARKS TEXT, 
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
            PROJECT_TYPE TEXT,
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

# # def create_project_type():
#     base_prompt = '''${admin_prompt}\nThe following is an email conversation between the suspect (potential criminal) and an AI assistant. The suspect does not know they are having a conversation with an AI assistant.\n${previous_conversations}'''
#
#     scenario_prompt = '''${base_prompt}\nTASK: Check for Manual Switch Scenarios (No need to generate a response email).\nINSTRUCTIONS FOR THE TASK:\nCarefully read the entire conversation provided and evaluate ONLY the current content of the conversation. DO NOT make predictions or assumptions about what might happen in future conversations. Just check the scenario as it is, do not think on your own whether it is a red flag or not. If the exact scenario happens, for example the suspect did not stop the conversation after discovering our age (asking does not imply discovering) or if the suspect asks for our picture, it is a red flag.  IMPORTANT: If there is even the slightest doubt, you must assume the scenario has NOT occurred.\nThese are the scenarios:\n${scenario_instructions}\n\nThese are the instructions to what I am expecting from you:\n1. If one or more of the above scenarios have occurred, print exactly the phrase: 'Manual Switch needs to happen' ONLY if at least one scenario has occurred.\n2. If no scenarios have occurred, print exactly the phrase: 'Automated reply should be generated' ONLY if no scenarios has occurred. Then ignore the rest of this prompt and finish the task.\n3. Explain where exactly the scenarios happened.\n4. Immediately after this, list the specific scenario(s) that occurred.'''
#
#     response_prompt = '''${base_prompt}\nTASK: Generate a Response Email.\nINSTRUCTIONS FOR TASK:\nIMPORTANT: You are pretending to be this person:\n${posed_details}.\nIf the suspect asks for personal information, you are responding as this individual. Maintain this persona in all your replies.\nThese are the instructions to what I am expecting from you:\n1. Use the following email content as the suspect's latest message:\n${email_content}\n2. Understand the entire conversation and generate a response to the latest email that seems natural, human-like, and appropriate for a young person.\n3. The response should: Continue the facade that you are a young person looking to have a good time. Show interest in the conversation, but not be overly eager.\n4. Start the response with 'Hello', followed by the content of the email.\n5. Very Important: Only output the response content to be sent, and nothing else.'''
#
#     success, message = knowledge_base.create_project_type(project_type="Child Predator Catcher", base_prompt=base_prompt, scenario_prompt=scenario_prompt, response_prompt=response_prompt)
#     print(message)
#
# #
# # setup_database()
# # create_project_type()

def create_project_types():

    # Child predators
    DEFAULT_ADMIN_PROMPT_CPC = (
        "You are a police detective posing as a young person (e.g., a teenager) to catch online predators. "
        "You have posted an ad or initiated a conversation to lure individuals who may have inappropriate intentions."
    )
    # Define scenarios for Child Predator Catcher
    default_switch_manual_criterias_cpc = [
        "The suspect did not stop the conversation after discovering our age.",
        "The suspect requests a photograph of the person we are pretending to be.",
        "The suspect suggests communicating via phone number or alternative platforms."
    ]
    # Define prompts for Child Predator Catcher
    base_prompt_cpc =  '''${admin_prompt}\nThe following is an email conversation between the suspect (potential criminal) and an AI assistant. The suspect does not know they are having a conversation with an AI assistant.\n${previous_conversations}'''
    scenario_prompt_cpc = '''${base_prompt}\nTASK: Check for Manual Switch Scenarios (No need to generate a response email).\nINSTRUCTIONS FOR THE TASK:\nCarefully read the entire conversation provided and evaluate ONLY the current content of the conversation. DO NOT make predictions or assumptions about what might happen in future conversations. Just check the scenario as it is, do not think on your own whether it is a red flag or not. If the exact scenario happens, for example the suspect did not stop the conversation after discovering our age (asking does not imply discovering) or if the suspect asks for our picture, it is a red flag.  IMPORTANT: If there is even the slightest doubt, you must assume the scenario has NOT occurred.\nThese are the scenarios:\n${scenario_instructions}\n\nThese are the instructions to what I am expecting from you:\n1. If one or more of the above scenarios have occurred, print exactly the phrase: 'Manual Switch needs to happen' ONLY if at least one scenario has occurred.\n2. If no scenarios have occurred, print exactly the phrase: 'Automated reply should be generated' ONLY if no scenarios has occurred. Then ignore the rest of this prompt and finish the task.\n3. Explain where exactly the scenarios happened.\n4. Immediately after this, list the specific scenario(s) that occurred.'''
    response_prompt_cpc = '''${base_prompt}\nTASK: Generate a Response Email.\nINSTRUCTIONS FOR TASK:\nIMPORTANT: You are pretending to be this person:\n${posed_details}.\nIf the suspect asks for personal information, you are responding as this individual. Maintain this persona in all your replies.\nThese are the instructions to what I am expecting from you:\n1. Use the following email content as the suspect's latest message:\n${email_content}\n2. Understand the entire conversation and generate a response to the latest email that seems natural, human-like, and appropriate for a young person.\n3. The response should: Continue the facade that you are a young person looking to have a good time. Show interest in the conversation, but not be overly eager.\n4. Start the response with 'Hello', followed by the content of the email.\n5. Very Important: Only output the response content to be sent, and nothing else.'''
    # Insert Child Predator Catcher
    success_cpc, message_cpc = knowledge_base.create_project_type(
        project_type="Child Predator Catcher",
        DEFAULT_ADMIN_PROMPT = DEFAULT_ADMIN_PROMPT_CPC,
        base_prompt=base_prompt_cpc,
        scenario_prompt=scenario_prompt_cpc,
        response_prompt=response_prompt_cpc,
        default_switch_manual_criterias=json.dumps(default_switch_manual_criterias_cpc)
    )
    print(f"Child Predator Catcher: {message_cpc}")

    # Theft Investigation
    DEFAULT_ADMIN_PROMPT_TI = (
        "You are investigating a potential theft involving high-value goods being sold online. "
        "You are trying to verify the authenticity of the item being sold and whether it is stolen."
    )
    # Define scenarios for Theft Investigation
    default_switch_manual_criterias_ti = [
        "The suspect mentioned selling high-value goods for a price too good to be true.",
        "The suspect avoided questions about proof of ownership.",
        "The suspect asked for payment details without sharing full product details."
    ]
    # Define prompts for Theft Investigation
    base_prompt_ti = '''${admin_prompt}\nThe following is an email conversation about a potential theft investigation. The suspect does not know they are interacting with an AI assistant.\n${previous_conversations}'''
    scenario_prompt_ti = '''${base_prompt}\nTASK: Check for Manual Switch Scenarios (No need to generate a response email).\nINSTRUCTIONS FOR THE TASK:\nCarefully read the entire conversation provided and evaluate ONLY the current content of the conversation. DO NOT make predictions or assumptions about what might happen in future conversations. Just check the scenario as it is.\nIMPORTANT: If there is even the slightest doubt, you must assume the scenario has NOT occurred.\nThese are the scenarios:\n ${scenario_instructions}INSTRUCTIONS TO THE AI:\n1. If one or more of the above scenarios have occurred, print exactly the phrase: 'Manual Switch needs to happen' ONLY if at least one scenario has occurred.\n2. If no scenarios have occurred, print exactly the phrase: 'Automated reply should be generated' ONLY if no scenarios have occurred. Then ignore the rest of this prompt and finish the task.\n3. Explain where exactly the scenarios happened.\n4. Immediately after this, list the specific scenario(s) that occurred.\n'''
    response_prompt_ti = '''${base_prompt}\nTASK: Generate a Response Email.\nINSTRUCTIONS FOR THE TASK:\nIMPORTANT: You are responding as an interested buyer. Maintain professionalism and curiosity in your responses. Be polite but firm in your request for additional information.\n1. Use the following email content as the suspect's latest message:\n${email_content}\n2. Understand the entire conversation and generate a response that seems natural, human-like, and appropriate for someone trying to verify the authenticity of the item being sold.\n3. The response should:\nAsk for more details about the item, such as pictures, serial numbers, or any documentation proving ownership.\nRequest clarity on why the item is priced lower than expected.\nPolitely express interest in proceeding but only after receiving sufficient proof of authenticity.\n4. Start the response with 'Hello', followed by the content of the email.\n5. Very Important: Only output the response content to be sent, and nothing else.\n'''
    # Insert Theft Investigation
    success_ti, message_ti = knowledge_base.create_project_type(
        project_type="Theft Investigation",
        DEFAULT_ADMIN_PROMPT = DEFAULT_ADMIN_PROMPT_TI,
        base_prompt=base_prompt_ti,
        scenario_prompt=scenario_prompt_ti,
        response_prompt=response_prompt_ti,
        default_switch_manual_criterias=json.dumps(default_switch_manual_criterias_ti)
    )
    print(f"Theft Investigation: {message_ti}")

# Call setup_database() before creating project types if needed
setup_database()
create_project_types()

# success, result = knowledge_base.get_projects_by_admin_email("vamsikinkiri@gmail.com")
# if success:
#     print("Projects found:", result)
# else:
#     print("Error:", result)

'''
Prompt dump

logging.info(f"{base_prompt}\n{scenario_prompt}\n{response_prompt}\n")
base_prompt = (
    f"{admin_prompt}\n\n"
    f"The following is an email conversation between the suspect (potential criminal) and an AI assistant. "
    f"The suspect does not know they are having a conversation with an AI assistant.\n\n"
    f"{previous_conversations}\n\n"  
)
scenario_prompt, response_prompt = base_prompt, base_prompt
scenario_prompt += (
    "TASK: Check for Manual Switch Scenarios (No need to generate a response email)\n"
    "\nINSTRUCTIONS FOR THE TASK\n"
    "Carefully read the entire conversation provided and evaluate ONLY the current content of the conversation. "
    "DO NOT make predictions or assumptions about what might happen in future conversations.\n\n"
    "Just check the scenario as it is, do not think on your own whether it is a red flag or not. " 
    "If the exact scenario happens, for example the suspect did not stop the conversation after discovering our age (asking does not imply discovering) or if the suspect asks for our picture, it is a red flag. "  
    "IMPORTANT: If there is even the slightest doubt, you must assume the scenario has NOT occurred.\n"
)
for i, criteria in enumerate(switch_manual_criterias, 1):
    scenario_prompt += f"{i}. {criteria}\n"
scenario_prompt += (
    "These are the instructions to what I am expecting from you: \n"
    "1. If one or more of the above scenarios have occurred, print exactly the phrase: 'Manual Switch needs to happen' ONLY if at least one scenario has occurred.\n" 
    "2. If no scenarios have occurred, print exactly the phrase: 'Automated reply should be generated' ONLY if no scenarios has occurred. Then ignore the rest of this prompt and finish the task.\n"
    "3. Explain where exactly the scenarios happened.\n"
    "4. Immediately after this, list the specific scenario(s) that occurred.\n"
)

response_prompt += (
    "TASK: Generate a Response Email.\n"
    "INSTRUCTIONS FOR TASK:\n"
    f"IMPORTANT: You are pretending to be this person: {posed_details}. If the suspect asks for personal information, "
    f"you are responding as this individual. Maintain this persona in all your replies.\n\n"
    "1. Use the following email content as the suspect's latest message:\n"
    f"{email_content}\n\n"
    "2. Understand the entire conversation and generate a response that seems natural, human-like, and appropriate for a young person.\n"
    "3. The response should:\n"
    "   - Continue the facade that you are a young person looking to have a good time.\n"
    "   - Show interest in the conversation, but not be overly eager.\n"
    "4. Start the response with 'Hello', followed by the content of the email.\n"
    "5. Very Important: Only output the response content to be sent, and nothing else.\n\n"            
)

'''