# Craigslist SafeBot - Help Documentation

## Overview

Craigslist SafeBot is an **AI-driven law enforcement tool** designed to assist in identifying and engaging with potential online predators or perpetrators via **email-based interactions**. The system integrates **AI automation**, **keyword-based scoring**, and **manual intervention mechanisms** to enhance crime investigations.

Craigslist SafeBot is developed to support **UC Riverside Police Department** by providing an efficient system for monitoring, detecting, and managing suspicious online activities through **automated email interactions**. By combining AI automation, real-time monitoring, and human intervention, the system allows law enforcement officers to focus on **high-priority cases**.

The primary objectives of Craigslist SafeBot include:

- **Baiting Suspects:** Initiate conversations with potential offenders on monitored online marketplaces (e.g., Craigslist).
- **Automated Engagement:** AI-driven chatbot generates realistic, context-aware email responses.
- **Risk Assessment:** The system assigns scores to conversations based on keyword occurrences and user interactions.
- **Manual Intervention:** Detectives can take over conversations when specific risk thresholds are exceeded.
- **User Profiling:** Tracking and analyzing email engagement history of suspects.
- **Scalability:** The modular design ensures easy adaptability for future enhancements.

## Application Features

- **Secure Login & Admin Management:** Allows authorized personnel to access the system.
- **Project Creation & Management:** Enables admins to create and configure new investigative projects.
- **Email Processing:** Securely retrieves and categorizes emails using **IMAP and SMTP protocols**.
- **Interaction Scoring:** Assigns risk scores to email conversations based on predefined **crime-specific keywords**.
- **AI-Based Response Generation:** Utilizes **LLM-powered chatbot** for realistic and adaptive email replies.
- **Manual vs Automated Switching:** System escalates cases requiring manual intervention based on interaction scores.
- **User Profiling & Tracking:** Maintains records of suspect interactions, behavioral patterns, and engagement levels.
- **Real-time Monitoring & Alerts:** Detects suspicious interactions and alerts administrators to take necessary actions.
- **Data Security & Compliance:** Ensures secure storage of sensitive data using **PostgreSQL**, with access restricted to authorized personnel only.

Craigslist SafeBot provides a **comprehensive suite of tools** for law enforcement agencies to **monitor, engage, and profile** suspects efficiently while maintaining **data privacy, security, and investigative accuracy**.

## Web Application Views & Functionalities

### **Login**

#### **Description:**
The login page is the entry point for administrators. It ensures that only authorized personnel can access the system, preventing unauthorized access to sensitive information.

#### **Fields & Inputs:**
- **Email ID:** Admin’s registered email.
- **Password:** Secure login credentials.
- **Login Button:** Triggers authentication and grants access to the dashboard.
- **Create Account Link:** Redirects users to the **Create Admin Account** page if they don’t have an account.

#### **How It Works:**
1. The admin enters their **Email ID** and **Password**.
2. Clicking the **Login Button** submits the credentials for verification.
3. If credentials are valid, the system redirects the admin to the **Dashboard**.
4. If invalid, an error message prompts the user to re-enter credentials.
5. Users can navigate to the **Create Account** page if they don’t have an account.

![Login_Page](/static/UI_Images/Login_Page.png)



### **Create Admin Account**

#### **Description:**
This page allows new administrators to register and create an account to access the system.

#### **Fields & Inputs:**
- **Email ID:** The email that will be used for login.
- **Password:** Secure password entry.
- **Confirm Password:** Ensures password confirmation.
- **Phone Number (Optional):** Contact number for notifications.
- **Affiliation (Optional):** Organization or law enforcement unit name.
- **Create Account Button:** Registers a new admin account.
- **Log in here Link:** Redirects to the **Login Page** if the user already has an account.

#### **How It Works:**
1. The admin fills out the required fields (**Email ID, Password, Confirm Password**).
2. Optional fields (**Phone Number, Affiliation**) can be provided.
3. Clicking **Create Account** submits the form.
4. The system verifies inputs and creates the account.
5. If successful, the admin is redirected to the **Login Page**.
6. If there’s an issue (e.g., email already exists), an error message is displayed.

![Create Admin Account Page](/static/UI_Images/Create_An_Account.png)


### **Active Projects**

#### **Description:**
This page allows users to view and manage existing projects, search for specific cases, and create new projects.

#### **Fields & Inputs:**
- **Search Bar:** Enables users to search for a specific project.
- **Search Button:** Filters projects based on search input.
- **Create New Project Button:** Opens the project creation page.
- **Project Cards:** Displays details like project name, associated email, last updated date, and available actions.
- **Open Project Button:** Redirects to the project details view.
- **Delete Project Button:** Removes the project from the system.

![Active Projects Page](/static/UI_Images/All_Projects_View_LoginProject.png)


### **Project Creation**

#### **Description:**
Provides administrators with a structured, step-by-step process to set up and customize new investigation projects efficiently.

#### **Project Creation Sections:**

##### **Project Information**
- **Project Name:** Name of the case.
- **Project Type:** Defines the type of investigation (e.g., Child Exploitation, Fraud, Theft, etc.).
    - Selecting a **Project Type** pre-populates default **conditions, AI Prompt, and intervention criteria**, which can be customized by the user.
- **Email ID:** Used for bait interactions. This is mandatory.
- **Password (App Password):** Secure authentication.

![Project Information](/static/UI_Images/Project_Creation_Page1_Project_Info.png)

##### **Bot Interaction Settings**
- **Response Frequency:** Determines how frequently AI responds to emails. Higher values mean more frequent responses, which can increase engagement scores.
- **Active Start/End Time:** Defines the operational window for AI responses, ensuring activity aligns with case needs.
- **Timezone Selection:** Sets the relevant timezone for interaction timestamps.

![Bot Interaction Settings](/static/UI_Images/Project_Creation_Page2_Bot_interaction.png)

##### **Engagement Thresholds**
- **Automated Engagement Threshold:** The risk score threshold below which AI continues responding autonomously.
- **Manual Engagement Threshold:** The risk score threshold above which AI stops and requires manual intervention.

![Engagement Thresholds](/static/UI_Images/Project_Creation_Page3thresholds.png)

##### **Admin Authorization**
- **Authorized Emails:** List of users granted access to monitor and manage the project. This is mandatory. 
- **Notifications:** Authorized emails receive alerts when they are added to a project and for other relevant events.

![Admin Authorization](/static/UI_Images/Project_Creation_Page4_Admin_authorization_emails.png)

##### **Manual Intervention Criteria**
- **Depends on Project Type:** Different project types have pre-defined manual intervention conditions. User can add more conditions/criterias.
- **Conditions requiring admin intervention:**

- **For example: Child Trafficking Cases:**
    - The suspect attempts to arrange an in-person meeting.
    - The suspect requests identifying information (e.g., address, school, parental details).
    - The suspect insists on moving the conversation to another platform.
    - The suspect offers monetary transactions in exchange for illegal activities.

![Manual Intervention Criteria](/static/UI_Images/Project_Creation_Page5_Manual_intervention_critera.png)

##### **Interaction Settings**
- **Posed Name:** Alias used in AI interactions.
- **Posed Age:** Simulated age to match investigation needs.
- **Posed Gender:** Selection of gender identity for engagements.
- **Posed Location:** Sets the geographical identity of the bot persona.

![Interaction Settings](/static/UI_Images/Project_Creation_Page6_interaction_settings.png)

##### **Keyword Prioritization**
- **Custom Keywords & Frequencies:** Enables admins to specify keywords that indicate risk, allowing for more refined threat assessment.
- **Keyword-Based Scoring:**
  - Each keyword is assigned a score, contributing to the final engagement risk level.
  - Higher frequency keywords lead to **higher engagement scores**, increasing the likelihood of manual intervention.
  - This is mandatory.


![Active Projects Page](/static/UI_Images/All_Projects_View_LoginProject.png)

### **Email Threads & Filters**

#### **Description:**
The index page provides a centralized view of all email interactions, enabling law enforcement officers to monitor and analyze email threads for potential threats.

#### **Features:**
- **Email Threads Display:** Lists ongoing and past email conversations related to investigations.
- **Manual vs Automated Responses:** Indicates whether replies were generated by AI or manually entered by investigators.
- **Scoring System:** Assigns a risk score to each conversation based on keyword frequency.
- **Reply Functionality (↩️):** Allows officers to send replies manually if needed.
- **Email Expansion (⬇️):** Users can click on an email to expand the conversation and view complete details.
- **Toggle Buttons (🔴🟢):** Enables switching between **manual (red) and automated (green)** responses.
- **Archive Email Button (📂):** Allows officers to archive emails, moving them to the **Archived Emails** section.
- **Sorting Emails (⏳🔢):** Emails can be sorted by **time** and **score** for better prioritization.
- **Default View (📅):** Displays email interactions from the **last 60 days** by default.

![Index Emails](/static/UI_Images/Index_Emails.png)

### **Manual vs Automated Modes**

#### **Automated Mode (🟢):**
- In this mode, responses are **automatically generated** by the system using **Large Language Models (LLMs)**.
- AI replies are crafted based on the **project prompt** set by the user for the specific investigation.
- The system analyzes incoming emails, calculates a **risk score** based on **keyword frequency**, and determines the most appropriate AI-generated response.
- The bot responds within the **active hours** defined during project creation.
- This allows for **efficient handling** of email interactions while maintaining engagement with suspects.

#### **Manual Mode (🔴):**
- The system switches to **manual mode** under the following conditions:
  - When **manual intervention criteria** (defined during project setup) are triggered.
  - If the **conversation score** exceeds the threshold **set by the user**.
  - When the detective manually toggles to **manual mode** to take control of the conversation.
- In this mode, AI-generated responses are **disabled**, and the detective must manually compose replies.

### **Expanded Email View**

#### **Description:**
Provides a **detailed view** of individual email conversations, including timestamps, sender/receiver information, and message content.

#### **Features:**
- **Complete Email History:** Shows the entire conversation for better context.
- **Manual Takeover:** Detectives can manually intervene if a conversation reaches a certain risk level.

![Expanded Email](/static/UI_Images/Index_Email_expand.png)

### **Search & Filtering Options**

#### **Description:**
Enhances usability by allowing officers to filter and search for relevant email interactions.

#### **Filtering Options:**
- **Search by Email Address (From/To):** Finds specific email conversations.
- **Search by Subject or Content:** Allows searching based on keywords.
- **Date Range Filters (📅):** Users can select custom start and end dates.
- **Relevant Keywords Filter (🔍):** Filters conversations containing high-risk words.
- **Top K Email Threads:** Users can enter a value for **K** to display the top-ranked email conversations based on score.
- **Last 30/60 Days Quick Filters (📆):** Allows fast access to recent interactions.
- **Customize Search Filters (⚙️):** Enables advanced filtering options, including **date, email addresses, score, and keywords**.
- **Clear Filters Button (🚫):** Resets search criteria for a fresh query.

![Search Filters](/static/UI_Images/Index_Search_filters.png)

### **Archived Emails**

#### **Description:**
Provides access to all archived emails, allowing investigators to review and restore conversations as needed.

#### **Features:**
- **Filter Archived Emails:** Users can search archived emails by sender, subject, content, and date range.
- **Relevant Keywords:** Highlights key terms that contributed to the email being archived.
- **Restore Emails (🔄):** Investigators can restore archived emails back to the active email list.

![Archived Emails](/static/UI_Images/Archived_Emails.png)


### **Suspect Profiles**

#### **Description:**
Provides an overview of suspect profiles detected through email interactions, enabling investigators to monitor and track activity.

#### **Features:**
- **Email Search:** Allows searching for suspect profiles using their email address.
- **Scoring System:** Displays the risk score for each suspect based on email interactions.
- **Last Active Time:** Shows the last recorded activity for each suspect.
- **Contact Information:** Displays any available contact details of suspects.
- **Action Remarks (📝):** Investigators can add and save custom remarks for each suspect.
- **Apply Filters Button (🔍):** Enables users to filter profiles based on risk score or last active time.

![Suspect Profiles](static/UI_Images/Suspect_Profiles.png)

<img src="{{ url_for('static', filename='UI_Images/Suspect_Profiles.png') }}" alt="Suspect Profiles">


### **Manage Profile**

#### **Description:**
Allows users to view and update their profile information.

#### **Features:**
- **View Profile Details:** Displays the registered email ID, phone number, and affiliation.
- **Update Profile Button (🔄):** Allows users to modify their contact details and affiliation.
- **Back to Dashboard Link (⬅️):** Provides a quick way to return to the main dashboard.

![Manage Profile](static/UI_Images/Manage_Profile.png)

### **Project Settings**

#### **Description:**
Enables administrators to configure key project parameters such as response settings, keyword management, and intervention criteria.

#### **Features:**
- **Response Frequency Settings:** Defines how frequently automated responses should be sent. A lower frequency results in fewer but more targeted responses, while a higher frequency ensures continuous engagement.
- **Engagement Thresholds:** Specifies when a conversation should transition to manual mode. If a message's score surpasses a certain threshold, the system automatically flags it for manual review.
- **Active Hours:** Allows setting project-specific active response times. The bot will only send automated responses within this timeframe.
- **Keyword Management:** Enables adding or updating high-priority keywords. These keywords influence the scoring mechanism, where more frequent matches increase the score, prioritizing the conversation.
- **Admin Authorization:** Defines authorized emails for project notifications. Admins will receive updates regarding flagged interactions, project modifications, and key events.
- **Manual Intervention Criteria:** Lists conditions under which manual intervention is required. These criteria are project-dependent and can be customized for each case type.
- **Bot Settings:** Configures automation behavior, such as default response templates and preferred AI model interactions.
- **Update Project Button (🔄):** Saves any changes made to the project settings.

![Project Settings](static/UI_Images/Project_Settings.png)

### **Contact Us**

#### **Description:**
Provides support contact details for users who need assistance.

#### **Features:**
- **Email Support Contacts:** Lists available email addresses for technical support.
- **Expected Response Time:** Notifies users about estimated response time (3-4 business days).
- **Working Hours:** Displays support availability (Monday - Friday, 9:00 AM - 5:00 PM PST).
- **Go to Help Page Button (📄):** Redirects users to additional support resources.
- **Back to Dashboard Link (⬅️):** Provides a quick return to the main dashboard.

![Contact Us](static/UI_Images/Contact_us.png)








