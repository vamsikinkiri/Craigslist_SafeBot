# Craigslist SafeBot

## Overview
Craigslist SafeBot is a **law enforcement tool** designed to assist the **UC Riverside Police Department** in identifying and engaging with potential online predators or perpetrators through **email-based interactions**. The system integrates **AI-driven email automation**, **keyword-based risk scoring**, and **manual intervention mechanisms** to enhance online crime investigations.

## Purpose
The primary objectives of Craigslist SafeBot are:

- **Baiting Suspects:** Initiate conversations with potential offenders on monitored online marketplaces (e.g., Craigslist).  
- **AI-Driven Engagement:** Utilize an **LLM-powered chatbot** to generate **realistic, context-aware responses**.  
- **Keyword-Based Risk Assessment:** Analyze email interactions in real-time and **assign risk scores** based on suspicious keywords.  
- **Automated to Manual Switching:** When a conversation meets specific criteria or risk score thresholds, the system **automatically hands over control** to a human officer.  
- **User Profiling & Evidence Collection:** Maintain records of **suspect interactions, contact details, and behavioral patterns** for law enforcement analysis.

By combining **AI automation, real-time monitoring, and human intervention**, Craigslist SafeBot enhances the efficiency of **online crime investigations**, allowing law enforcement officers to focus on **high-priority cases**.

---

## Project Setup Instructions

### 1. Install Dependencies
The project requires several Python libraries, which are listed in `requirements.txt`. These dependencies include:
- **Flask** - Web framework.
- **flask-login** - User authentication.
- **WTForms** - Web form handling.
- **psycopg2** - PostgreSQL database connection.
- **bcrypt** - Password hashing and security.
- **pyyaml** - YAML file parsing.
- **langchain-groq** - LLM integration (Groq API).
- **apscheduler** - Background task scheduling.
- **werkzeug** - Security and utility functions.

To install all required dependencies, run the following command:

```bash
pip3 install -r requirements.txt
```

---

## 2. Setup PostgreSQL Database

The project **requires a PostgreSQL database** to store:
- **User and admin accounts**
- **Email threads and interaction data**
- **Keyword-based risk scores**
- **Project settings and configurations**

### **Installing PostgreSQL**
Follow the **official PostgreSQL installation guide** based on your operating system and create a database for the website to use.

#### **Providing Database Credentials**
After setting up PostgreSQL, update the `credentials.yaml` file with your database details:

```yaml
postgresql:
  pg_host: "your-database-host"
  pg_database: "your-database-name"
  pg_user: "your-database-username"
  pg_password: "your-database-password"
  pg_port: 5432
```

---

## 3. LLM API Key Setup

The system uses an **open-source Large Language Model (LLM)** to analyze conversations and generate realistic email responses. To enable this functionality:

### Step 1: Obtain an LLM API Key
- We have used GroqCloud to register for an API key. Go to [Groq](https://console.groq.com/) or any other supported LLM provider (would need changes in `response_generator.py`) and generate an API key.
- Retrieve your **Groq API Key** from your account dashboard.
- Decide on which model to be used to analyze and generate responses.

### Step 2: Update the Credentials File
Once you have the API key and the model, update the `credentials.yaml` file with the following details:

```yaml
llm:
  groq_api_key: "your-api-key"
  model_name: "model_name"
```

---

## 4. Database Table Setup and Initialization

The `db_tables_setup.py` file is responsible for creating the necessary database tables and initializing essential entries required for the project. This file ensures that the PostgreSQL database is properly structured for storing all project-related data.

### **Key Functions of `db_tables_setup.py`**

1. **Creating New Tables**:
   - Creates essential tables for storing project data:
     - `EMAIL_THREADS`: Tracks email conversations, interaction scores, and response states.
     - `SCORED_EMAILS`: Stores email scoring data linked to conversations.
     - `USER_PROFILES`: Maintains user-specific data such as contact information, activity status, and remarks of all suspects (users).
     - `ADMIN_ACCOUNTS`: Manages admin accounts for accessing the system.
     - `PROJECTS`: Contains project-level configurations, thresholds, and keywords.
     - `PROJECT_TYPES`: Stores predefined project types, including prompts and switch criteria.

2. **Setting Up Default Entries**:
   - Predefines project types with specific prompts for scenarios like:
     - **Child Predator Catcher**
     - **Theft Investigation**
   - Prompts include:
     - **Base Prompt**: General prompt instructions for the LLM.
     - **Scenario Prompt**: Prompt to check for conditions to determine if a manual switch is required.
     - **Response Prompt**: Prompt for generating AI responses to email interactions.

3. **Run the Script**:
   Execute the script to create the tables, and initialize default entries:
   ```bash
   python3 db_tables_setup.py
   ```
---

## 5. Running the Project
1. **Ensure all the requirements are installed and PostgreSQL is running** on your system.
2. **Ensure `credentials.yaml` is properly configured with PostgreSQL and LLM parameters**
3. **Initialize the database tables by running `db_tables_setup.py`**.
4. **Run the Flask Application:**
    ```bash
    flask --app app run
    or
    python3 app.py
   ```
5. **Access the website in your local system (The port number might change depending on where the flask application is run):**
    ```cpp
    http://127.0.0.1:5000
    ```
---

## 6. Initial Website Setup

When the website is loaded for the first time, you will need to create an admin account and then proceed to create a project for bait engagement. This is assuming you have already set up the bait engagement post on Craigslist or any other monitored online marketplaces. This ensures that the chatbot receives emails to investigate. Below are detailed steps and explanations for each step.

---

### **Step 1: Create Admin Account**

1. Navigate to the **Admin Account Creation Page**.
2. Provide the following details:
   - **Email ID**: The admin's email address (e.g., detective or supervisor email).
   - **Password**: Set a secure password for the admin account.
   - **Phone Number (Optional)**: Enter the admin's phone number if required.
   - **Affiliation (Optional)**: Enter any relevant organizational information.
3. Click on **Create Account** to set up the admin account.

---

### **Step 2: Create a Project**

Once the admin account is created, log in using those credentials and proceed to the **Project Creation Page**. Below is an explanation of each term and its significance:

#### **1. Project Information**
- **Project Type**: Choose the type of project (e.g., Child Predator Catcher or Theft Investigation).
- **Project Name**: Enter a unique name for the project.
- **Email**: Provide the email that was used in the bait engagement.
- **App Password**: Generate an app password for the provided email. Use the [App Passwords](https://support.google.com/accounts/answer/185833?hl=en) link for detailed instructions.

#### **2. Bot Interaction**
- **Safe Bot Settings**: Provide specific instructions for the LLM, such as the goal of the engagement and the tone of responses.
- **Response Frequency**: Define how often replies should be sent (e.g., every 10 minutes after an email is received).

#### **3. Engagement Thresholds**
- **Automated Engagement Threshold**: The minimum risk score required to automatically generate a reply.
- **Manual Engagement Threshold**: The maximum risk score after which the case will be handed over to detectives for manual investigation.

#### **4. Admin Authorization**
- **Authorized Emails**: Add email addresses of admins or detectives authorized to access the project and its information.

#### **5. Manual Intervention Criteria**
- **Scenarios**: Define specific scenarios that trigger manual intervention. Some predefined scenarios:
  - The suspect did not stop the conversation after discovering the person is underage.
  - The suspect requests a photograph of the person we are pretending to be.
  - The suspect suggests communicating via phone number or alternative platforms.

#### **6. Interaction Settings**
- **Posed Details**: Enter the details of the individual you posed as in the bait post:
  - Name (e.g., Karen, Jason)
  - Age (e.g., 15 or 16)
  - Gender
  - Location (e.g., a nearby area where the suspect might engage).

#### **7. Keyword Prioritization**
- **Keywords and Their Frequencies**: Specify keywords that the chatbot should monitor and their frequency. These keywords will help calculate the risk score of the interaction.

---

### **Step 3: Finalize and Create Project**

Once all the required fields are filled:
1. Review the project details to ensure accuracy.
2. Click on **Create Project** to finalize and save the project.

You can manage active projects on the **Project Dashboard**, where you can:
- Open an existing project for monitoring or editing.
- Delete a project if it's no longer needed.


By following these steps, the Craigslist SafeBot will be set up and ready to engage in bait interactions efficiently.


---


# Project Dashboard Overview

The **Project Dashboard** is the central interface for managing ongoing investigations, monitoring email threads, and customizing project settings. Once a project is created, the chatbot periodically scans for new emails, analyzes conversations, and takes automated actions like generating responses, notifying admins in case of the need for manual takeover, or escalating scenarios for manual intervention.

Below is a detailed breakdown of the main features and options available on the dashboard:

---

### **1. Email Threads and Scores**
The dashboard displays all email threads related to the selected project. For each thread, the following details are shown:
- **Email Address**: The suspect's email address.
- **Subject**: The subject of the email thread.
- **Score**: The risk score is calculated based on keywords and engagement thresholds.
- **AI Response State**: 
  - **Green (Automated)**: The chatbot is handling the conversation automatically.
  - **Red (Manual)**: The conversation has been or will need to be taken over by the detectives.
- **Actions**:
  - **Archive Email Thread**: Archive the thread for completed investigations.
  - **Send Manual Reply**: Enable detectives to send replies via email directly using the website.

---

### **2. Customizable Search Filters**
Detectives can use the **Search Filters** to quickly locate specific email threads based on:
- **Email Address**
- **Risk Score**: Filter threads by score thresholds to prioritize high-risk cases.
- **Time/Date**: Narrow down threads based on the last activity timestamp.

---

### **3. Suspect Profiles**
The **Suspect Profiles** page provides a detailed view of all suspects associated with the project:
- **Primary Email**: The suspect's email address.
- **Risk Score**: The cumulative risk score calculated for the suspect.
- **Last Active**: The timestamp of the suspect's last email interaction.
- **Remarks**: Detectives can add action notes or observations for each suspect.
- **Filters**: Search suspects by email, risk score, or activity date.

---

### **4. Archived Emails**
Archived email threads can be accessed from the **Archived Emails** page. This allows detectives to review completed investigations while keeping the active dashboard uncluttered. The search bar on this page enables quick navigation through archived threads.

---

### **5. Project Settings**
Detectives can modify any and all project configurations currently set from the **Project Settings** page.


---

### **6. Manage Profile and Switch Projects**
- **Manage Profile**: Detectives can update their personal information and preferences.
- **Switch Projects**: Allows switching between active projects without logging out.

---

### **7. Automated and Manual Workflow**
The system ensures an efficient workflow:
- The chatbot monitors email threads in real time.
- Detectives can step in to manually handle conversations as needed.
- All actions, updates, and settings are logged to maintain full transparency and traceability.

This dashboard provides a comprehensive toolset for managing investigations, ensuring that both automated and manual workflows are seamlessly integrated into the system.

---

# Modular Architecture Overview

The system is designed using a modular architecture to ensure **scalability, maintainability, and efficient functionality**. Below is an overview of each Python module, its responsibilities, and how it interacts with other modules.

---

### **1. `app.py` - Main Application Entry Point**
- Initializes the **Flask application** and configures authentication with `flask-login`.
- Sets up the **project scheduler** to periodically process emails for all projects created.
- Defines **routes** for login, logout, project creation, and user account management.
- Manages **session-based authentication** and ensures secure session handling.

> **Key Components:**
> - Integrates all other modules into the application.
> - Implements a background scheduler to periodically process projects (`project_scheduler.process_projects`).
> - Handles **session security** and **user authentication**.

---

### **2. `auth_handler.py` - Authentication Management**
- Manages **user authentication** for admins (login and session management).
- Uses **bcrypt** for **password hashing** and **verification**.
- Fetches admin details from the **database (`knowledge_base.py`)** for authentication.
- Provides `LoginForm` for user authentication via Flask-WTF.

> **Key Components:**
> - Uses **secure password hashing** to authenticate users.
> - Retrieves and verifies user credentials stored in PostgreSQL.

---

### **3. `project_scheduler.py` - Background Processing**
- **Schedules periodic tasks** to fetch and analyze emails.
- Calls `email_handler.py` and `email_processor.py` to process **new conversations**.
- Retrieves **ongoing email interactions** and updates their status.

> **Key Components:**
> - Uses **APScheduler** to schedule **automatic email fetching**.
> - Filters **emails by date and keyword**.
> - Updates conversation statuses based on **risk scores**.

---

### **4. `email_handler.py` - Email Retrieval & Sending**
- Manages email **login, fetching, and processing**.
- Uses **IMAP** to access and retrieve emails from Gmail.
- Supports **email sending** via SMTP.
- Implements **email grouping** to organize and analyze email conversations based on thread IDs.

> **Key Components:**
> - Extracts **email content, metadata, and attachments**.
> - Fetches **thread-based conversations** and **filters** emails based on criteria.
> - Securely handles **SMTP login credentials**.

---

### **5. `email_processor.py` - Email Analysis & Workflow Automation**
- Processes **incoming emails** and updates **interaction history**.
- **Scores emails** based on keyword detection.
- Checks if the AI should continue responding or **switch to manual intervention** by analyzing the conversation history and checking for any predefined scenarios that trigger the change of state from automated to manual with the help of `response_generator.py`.
- Flags emails that **exceed predefined risk thresholds**.
- Notifies **detectives** if any of the scenarios occur or an email conversation crosses the manual engagement threshold.

> **Key Components:**
> - Implements **risk scoring** by analyzing email contents.
> - Calls `interaction_profiling.py` to assess **threat levels**.
> - Calls `response_generator.py` to anayze the **conversations**.
> - **Triggers admin alerts** when scenarios occur or thresholds are exceeded.

---

### **6. `interaction_profiling.py` - Risk Scoring Engine**
- **Assigns a cumulative score** to each email based on detected **keywords**.
- **Normalizes scores** between 0-100 based on keyword occurrences.

> **Key Components:**
> - Uses **regular expressions** to analyze email content.
> - **Dynamically tracks** keyword occurrences across conversations.
> - **Optimized scoring function** for real-time analysis.

---

### **7. `response_generator.py` - AI-Powered Reply System**
- Analyzes conversations to scan for any predefined scenarios and generates **realistic replies** using **LLMs** (e.g., Groq's Llama models).
- Uses `ChatGroq` to call the **LLM API** with custom prompt instructions.
- Dynamically **adjusts responses** based on risk assessment.

> **Key Components:**
> - Calls **LLMs** to generate **context-aware replies**.
> - Uses `credentials.yaml` for **secure API key storage**.
> - Adjusts response **temperature for more human-like interaction**.

---

### **8. `user_profiling.py` - Tracking Suspect Behavior**
- Tracks **suspect activity** based on email conversations.
- Extracts **contact details** (e.g., phone numbers) from emails.
- Maintains **email history per suspect** across projects.

> **Key Components:**
> - Implements **Regex-based phone number extraction**.
> - Updates suspect records in the **database**.
> - Detects **inactive users** and marks them accordingly.

---

### **9. `knowledge_base.py` - Database Interaction Layer**
- Serves as an API for all modules that need to interact with the PostgreSQL database, facilitating secure data retrieval and storage.
- Connects to the **PostgreSQL database** and manages:
  - **Admin accounts**
  - **Project details**
  - **Stored email conversations**
  - **Keyword-based scoring**
- Fetches project settings and **triggers automated actions**.

> **Key Components:**
> - **Implements database queries** for CRUD operations.
> - Manages **user authentication and authorization**.
> - Uses `psycopg2` for **secure database communication**.

---


### **10. Interactions Between Modules**
- `app.py` calls all other modules to **run the website and manage sessions**.
- `auth_handler.py` handles the **admin authentication**.
- `project_scheduler.py` **automates** email processing at intervals.
- `email_handler.py` retrieves emails, while `email_processor.py` analyzes them.
- `interaction_profiling.py` assigns **risk scores** based on keywords.
- `response_generator.py` analyzes conversations and generates **LLM-powered replies** based on analysis.
- `user_profiling.py` tracks **suspect engagement levels**.
- `knowledge_base.py` **stores and retrieves** all project-related data.


This modular design ensures **clear separation of concerns**, making the system **scalable, maintainable, and easily extendable**.

---

# API Endpoints

| Endpoint                   | Method  | Description |
|----------------------------|---------|-------------|
| `/login`                   | POST    | Admin login authentication |
| `/create_account`          | POST    | Admin account creation |
| `/all_projects_view`       | POST    | View and access all active projects |
| `/project_creation`        | POST    | Create a new investigation project |
| `/`                        | GET     | Main dashboard: Retrieve email threads for the project |
| `/update_project`          | PATCH   | Update project settings |
| `/update_account_profile`  | PATCH   | Update admin account settings |
| `/user_profiles`           | GET     | Extract all suspect profiles and display them |
| `/archived_emails`         | GET     | Extract all archived emails and display them|
| `/email_thread_reply/<id>` | POST    | Send a manual email response to an email with a particular id |

---

# Conclusion

This website is currently hosted on **University of California, Riverside (UCR) servers** and has been officially handed over to the **UC Riverside Police Department** for their use. 

The parameters in the `credentials.yaml` file included in this repository are configured for **local development and testing** and are **not** the actual credentials used in the deployed version of the website. 

Anyone interested in testing the application can **provide their own parameters, setup** (e.g., database credentials, LLM API key, email settings, initial website setup) and **run the website locally** following the setup instructions provided.

---

Thank you for your interest in **Craigslist SafeBot**! 🚀 If you have any questions or feedback, feel free to reach out.

---
