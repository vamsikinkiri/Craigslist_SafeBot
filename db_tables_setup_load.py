import hashlib
from datetime import datetime, timedelta
import pandas as pd
from db_helper import get_connection
import warnings
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)


crime_data_all = pd.read_csv('Crime_reports.csv')

## Only considering 2 years data for testing
crime_data_all['reportDate'] = pd.to_datetime(crime_data_all['reportDate'], errors='coerce')
crime_data_all['offenseDate'] = pd.to_datetime(crime_data_all['offenseDate'], errors='coerce')
two_years_ago = datetime.now() - timedelta(days=2*365)
crime_data = crime_data_all[(crime_data_all['reportDate'] >= two_years_ago) | (crime_data_all['offenseDate'] >= two_years_ago)]
crime_data.reset_index(drop=True, inplace=True)

crime_type_to_category = {
    'Other Assaults - Not Aggravated': 'Assault',
    'THEFT: Theft from motor vehicle': 'Theft',
    'ASSAULT: Firearm': 'Assault',
    'DRUG ABUSE VIOLATIONS': 'Drug-Related Crimes',
    'VANDALISM': 'Vandalism',
    'ASSAULT: Other Assaults': 'Assault',
    'OTHER: DUI': 'Driving Offenses',
    'WEAPONS: Carrying, Possessing, etc.': 'Weapons Violations',
    'OTHER: All Other Offenses': 'Miscellaneous Offenses',
    'ASSAULT: Other dangerous weapon': 'Assault',
    'SEX CRIMES': 'Sex Offenses',
    'OTHER: Stolen Property': 'Theft',
    'MOTOR VEH. THEFT: Autos': 'Theft',
    'THEFT: Shoplifting': 'Theft',
    'BURGLARY: Forcible entry': 'Burglary',
    'FRAUD: Embezzlement': 'Fraud',
    'THEFT: All other larceny': 'Theft',
    'FRAUD: Forgery & Counterfeiting': 'Fraud',
    'ROBBERY: Firearm': 'Robbery',
    'FRAUD: Other Fraud': 'Fraud',
    'MOTOR VEH. THEFT: Trucks and buses': 'Theft',
    'MOTOR VEH. THEFT: Other vehicles': 'Theft',
    'DRUG ABUSE VIOLATIONS: Drunkenness': 'Drug-Related Crimes',
    'ASSAULT: Strong-Arm': 'Assault',
    'ASSAULT: Knife or cutting instrument': 'Assault',
    'ROBBERY: Strong-Arm': 'Robbery',
    'THEFT: Theft of motor vehicle parts or accessories': 'Theft',
    'THEFT: Theft of bicycles': 'Theft',
    'BURGLARY: Unlawful entry - no force': 'Burglary',
    'SEX CRIMES: Sexual Assault': 'Sex Crimes',
    'OTHER: Offenses Against Family': 'Family Offenses',
    'THEFT: Theft from buildings': 'Theft',
    'THEFT: Theft from coin-operated machine or device': 'Theft',
    'DISTURBING THE PEACE: Disorderly Conduct': 'Disturbing the Peace',
    'THEFT: Pocket picking': 'Theft',
    'BURGLARY: Attempted forcible entry': 'Burglary',
    'ROBBERY: Knife or cutting instrument': 'Robbery',
    'OTHER: Curfew and Loitering': 'Curfew and Loitering',
    'DRUG ABUSE VIOLATIONS: Liquor Laws': 'Liquor Violations',
    'HOMICIDE: Murder & non-negligent manslaughter': 'Homicide',
    'GAMBLING': 'Gambling',
    'ROBBERY: Other dangerous weapon': 'Robbery',
    'SEX CRIMES: Prostitution/Vice': 'Sex Crimes',
    'THEFT: Purse snatching': 'Theft',
    'DESTRUCTION / DAMAGE / VANDALISM OF PROPERTY': 'Vandalism',
    'FAMILY OFFENSES, NONVIOLENT': 'Family Offenses',
    'SIMPLE ASSAULT': 'Assault',
    'BURGLARY/BREAKING AND ENTERING': 'Burglary',
    'ALL OTHER OFFENSES': 'Miscellaneous Offenses',
    'DRIVING UNDER THE INFLUENCE': 'Driving Offenses',
    'AGGRAVATED ASSAULT': 'Assault',
    'STOLEN PROPERTY OFFENSES': 'Theft',
    'KIDNAPPING / ABDUCTION': 'Kidnapping/Abduction',
    'MOTOR VEHICLE THEFT': 'Theft',
    'THEFT FROM BUILDING': 'Theft',
    'ALL OTHER LARCENY': 'Theft',
    'FALSEPRETENSES / SWINDLE / CONFIDENCEGAME': 'Fraud',
    'THEFT OF MOTOR VEHICLE PARTS OR ACCESSORIES': 'Theft',
    'WEAPON LAW VIOLATIONS': 'Weapons Violations',
    'CREDITCARD / AUTOMATED TELLER MACHINE FRAUD': 'Fraud',
    'SHOPLIFTING': 'Theft',
    'DISORDERLY CONDUCT': 'Disturbing the Peace',
    'TRESPASS OF REAL PROPERTY': 'Trespassing',
    'IMPERSONATION': 'Fraud',
    'ROBBERY': 'Robbery',
    'IDENTITYTHEFT': 'Fraud',
    'DRUG EQUIPMENT VIOLATIONS': 'Drug-Related Crimes',
    'DRUG NARCOTIC VIOLATIONS': 'Drug-Related Crimes',
    'THEFT FROM MOTOR VEHICLE': 'Theft',
    'POCKET-PICKING': 'Theft',
    'SEX CRIMES': 'Sex Crimes',
    'COUNTERFEITING / FORGERY': 'Fraud',
    'HACKING / COMPUTERINVASION': 'Cyber Crimes',
    'EMBEZZLEMENT': 'Fraud',
    'LIQUOR LAW VIOLATIONS': 'Liquor Violations',
    'INTIMIDATION': 'Assault',
    'PORNOGRAPHY / OBSCENEMATERIAL': 'Sex Crimes',
    'CURFEW / LOITERING / VAGRANCY VIOLATIONS': 'Curfew and Loitering',
    'EXTORTION / BLACKMAIL': 'Fraud',
    'WELFAREFRAUD': 'Fraud',
    'PROSTITUTION': 'Sex Crimes',
    'MURDER AND NON-NEGLIGENT MANSLAUGHTER': 'Homicide',
    'ARSON': 'Arson',
    'THEFT FROM COIN-OPERATED MACHINE OR DEVICE': 'Theft',
    'ANIMAL CRUELTY': 'Animal Crimes',
    'PURSE-SNATCHING': 'Theft',
    'HUMANTRAFFICKING ,SERVITUDE INVOLUNTARY': 'Human Trafficking',
    'WIREFRAUD': 'Fraud',
    'OPERATING / PROMOTING / ASSISTING GAMBLING': 'Gambling'
}
##Mapping Crime type to Category
crime_data['category'] = crime_data.loc[:, 'crimeType'].map(crime_type_to_category)

##Keywords of interest for each crime
crime_keywords = {
    "Theft": "stolen, missing, took, break-in, rob, purse, snatch, valuables, swipe, break, steal",
    "Assault": "attack, hit, hurt, fight, punched, violence, weapon, threaten, injured, abuse",
    "Drug-Related Crimes": "drugs, high, stoned, DUI, drunk, possession, pills, weed, substance, narcotics",
    "Vandalism": "vandalized, damage, graffiti, broke, spray, smashed, ruin, trash, wreck, destroyed",
    "Fraud": "scam, cheat, stolen identity, fake, trick, fraud, lie, phony, ripped off, forged",
    "Sex Crimes": "harassed, assaulted, inappropriate, molest, abuse, touched, violated, indecent",
    "Robbery": "robbed, hold-up, mugged, gun, took, cash, wallet, money, stole, armed",
    "Homicide": "killed, murder, shot, dead, stabbed, gun, homicide, death, body, weapon",
    "Kidnapping/Abduction": "kidnapped, took, child, missing, ransom, gone, stranger, grabbed",
    "Weapons Violations": "gun, weapon, armed, illegal, knife, shooting, discharge, firearm, loaded",
    "Driving Offenses": "driving, DUI, drunk, reckless, swerved, crash, speeding, influence",
    "Miscellaneous Offenses": "offense, crime, illegal, charge, violation, misconduct, unlawful, wrong",
    "Burglary": "break-in, trespass, forced, burglarized, smashed, robbed, intruder, house",
    "Family Offenses": "domestic, family, abuse, household, child, spouse, neglect, violent, argument",
    "Disturbing the Peace": "loud, noise, yelling, argument, disturbance, music, party, fight, scene",
    "Curfew and Loitering": "curfew, loiter, minors, wandering, hanging out, late, staying out, street",
    "Liquor Violations": "alcohol, drunk, drinking, underage, liquor, booze, public, intoxicated",
    "Gambling": "bet, gamble, wager, poker, casino, money, illegal, dice, cards",
    "Trespassing": "trespass, property, invade, break-in, yard, unauthorized, premises, unwelcome",
    "Cyber Crimes": "hacked, online, phishing, malware, identity theft, scam, internet, fraud",
    "Arson": "fire, burn, blaze, ignite, torch, set fire, arson, burned down, flame",
    "Animal Crimes": "animal, cruelty, abuse, neglect, dog, pet, harm, mistreat, fighting",
    "Human Trafficking": "trafficking, forced, smuggling, exploited, trapped, slavery, under control"
}

# def format_keywords_list(keywords):
#     return "{" + ", ".join([f'"{keyword.strip()}"' for keyword in keywords.split(",")]) + "}"
#
# crime_data['KEYWORDS_LIST'] = crime_data['category'].map(crime_keywords).fillna("").apply(format_keywords_list)
crime_data.loc[:,'KEYWORDS_LIST'] = crime_data['category'].map(crime_keywords).fillna("").apply(lambda x: '{' + x.replace(", ", ",") + '}')

crime_data.loc[:, 'category'] = crime_data['category'].fillna("Unknown")

crime_data.loc[:, 'crimeType'] = crime_data['crimeType'].fillna("Unknown")

# AI prompt function
def generate_ai_prompt(category):
    if category == "Theft":
        return "Could you share details on any items that went missing and where this happened? Any specifics you remember could be really helpful."
    elif category == "Assault":
        return "Can you describe what happened during the incident? If there were any injuries or weapons involved, please feel free to mention those details."
    elif category == "Drug-Related Crimes":
        return "If you noticed any substances or drug paraphernalia, could you let us know? Any context on how or where you observed it would be great."
    elif category == "Vandalism":
        return "Could you describe the damage or graffiti you noticed? Any details on the location or what might have been damaged would be useful."
    elif category == "Fraud":
        return "Could you explain what happened? If you noticed any unusual transactions or were tricked into giving out information, we’d like to know."
    elif category == "Sex Crimes":
        return "If you feel comfortable, could you tell us about the incident? Any information on what occurred and where it took place would help."
    elif category == "Robbery":
        return "Can you share what was taken, and any details you remember about the person or people involved? It’s important to know if a weapon was used."
    elif category == "Homicide":
        return "Could you share what you know about the incident, like where and when it happened, and any details about those involved?"
    elif category == "Kidnapping/Abduction":
        return "Please let us know what you observed. Any details about the person taken, location, or those involved could be crucial."
    elif category == "Weapons Violations":
        return "If you saw any weapons or suspicious items, could you describe them? Details on when and where you noticed them would help."
    elif category == "Driving Offenses":
        return "Could you tell us more about what happened? Any details on the vehicle or the person’s behavior could be helpful."
    elif category == "Miscellaneous Offenses":
        return "Please describe the situation in as much detail as you can. Any information you provide will be useful."
    elif category == "Burglary":
        return "Can you describe what was broken into and any items that were taken? Knowing the location and time can also be helpful."
    elif category == "Family Offenses":
        return "If possible, please share some details on the situation. Any context or background you think is important would be valuable."
    elif category == "Trespassing":
        return "Could you tell us where this occurred and if there were any signs of forced entry? Any details on the person involved would help."
    elif category == "Cyber Crimes":
        return "If you can, please describe the online activity you’re concerned about. Any specifics on the issue or how it affected you would be useful."
    elif category == "Arson":
        return "Can you share what you saw regarding the fire? Details on where it happened or if anyone was nearby would help us understand."
    elif category == "Human Trafficking":
        return "If you feel comfortable, please share what you observed. Any details on the people involved, location, or situation would help immensely."
    else:
        return f"Could you tell us more about this {category.lower()}? Any details about the people involved, location, or what happened would help."

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
def insert_into_email_categories(crime_data, cursor):

    crime_data.loc[:,'CATEGORY_ID'] = crime_data.apply(lambda row: generate_hash(row['category'] + row['crimeType']), axis=1)
    crime_data.loc[:,'CATEGORY_NAME'] = crime_data['category']
    crime_data.loc[:,'CRIME_TYPE'] = crime_data['crimeType']
    # crime_data['KEYWORDS_LIST'] = crime_data['category'].map(crime_keywords).fillna("")
    #crime_data.loc['KEYWORDS_LIST'] = crime_data['category'].map(crime_keywords).fillna("").apply(lambda x: '{' + x.replace(", ", ",") + '}')
    crime_data.loc[:,'AI_PROMPT_TEXT'] = crime_data['category'].apply(generate_ai_prompt)
    crime_data.loc[:,'LAST_UPDATED'] = datetime.now()
    final_data = crime_data[['CATEGORY_ID', 'CATEGORY_NAME', 'CRIME_TYPE', 'KEYWORDS_LIST', 'AI_PROMPT_TEXT', 'LAST_UPDATED']]

    # Define insert query
    insert_query = """
        INSERT INTO EMAIL_CATEGORIES (
            CATEGORY_ID, CATEGORY_NAME, CRIME_TYPE, 
            KEYWORDS_LIST, AI_PROMPT_TEXT, LAST_UPDATED
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (CATEGORY_ID) DO NOTHING;
    """

    for _, row in crime_data.iterrows():
        cursor.execute(insert_query, (
            row['CATEGORY_ID'], row['CATEGORY_NAME'], row['CRIME_TYPE'],
            row['KEYWORDS_LIST'], row['AI_PROMPT_TEXT'], row['LAST_UPDATED']
        ))

# Main function to set up tables and insert data
def setup_database():
    try:
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()

        # Create tables and insert data
        create_tables(cursor)
        insert_into_email_categories(crime_data, cursor)

        # Commit changes
        conn.commit()
        print("Tables created successfully.")

    except Exception as e:
        print("An error occurred:", e)

    finally:
        cursor.close()
        conn.close()
