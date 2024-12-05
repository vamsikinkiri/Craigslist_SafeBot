import logging
from datetime import datetime
from flask import session
from email_handler import EmailHandler
from knowledge_base import KnowledgeBase
from datetime import datetime, timedelta
from email_processor import EmailProcessor

email_handler = EmailHandler()
knowledge_base = KnowledgeBase()
email_processor = EmailProcessor()

class ProjectScheduler:

    def process_project(self, email_id, app_password, project_keywords, filters, project_name=None):
        if not filters['search_initiated'] and not filters['last_30_days'] and not filters['last_60_days']:
            filters['end_date'] = datetime.now().strftime('%Y-%m-%d')
            filters['start_date'] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            filters['last_30_days'] = True  # Ensure the button state is correct for initial load

        # Fetch, filter, and group emails
        if filters['search_initiated'] or filters['last_30_days'] or filters['last_60_days']:
            emails, grouped_emails, keywords = email_handler.fetch_emails_and_keywords(
                user=email_id,
                password=app_password,
                subject=filters['subject'], 
                content=filters['content'],
                start_date=filters['start_date'], 
                end_date=filters['end_date'],
                bidirectional_address=filters['bidirectional_address']
            )
        else:
            emails, grouped_emails, keywords = [], {}, []

        # Process the grouped emails
        email_processor.process_grouped_emails(grouped_emails, session_email=email_id, project_keywords=project_keywords)

        # Initialize dictionaries for latest timestamp and conversation scores
        latest_timestamp = {}
        conversations_score = {}

        # Extract the latest time and add the score for each conversation
        for thread_id, email_list in grouped_emails.items():
            # Extract the latest timestamp
            if email_list:  # Ensure the email_list is not empty
                latest_timestamp[thread_id] = email_list[0]['date']  # First email has the latest date

            # Fetch the conversation score
            score_success, score = knowledge_base.get_interaction_score(thread_id=thread_id)
            if not score_success:
                logging.error(f"Error fetching score for thread_id {thread_id}: {score}")
                continue

            conversations_score[thread_id] = score[0] if isinstance(score, (list, tuple)) else score
        
        #logging.info(f"Latest timestamps: \n{latest_timestamp}\nScores: \n{conversations_score}")


        # Filter emails by selected keyword
        if filters['selected_keyword']:
            grouped_emails = {key: details for key, details in grouped_emails.items()
                                ## Key
                            if any(filters['selected_keyword'].lower() in email['subject'].lower() or
                                    filters['selected_keyword'].lower() in email['content'].lower() for email in details)}
        
        return {
            "emails": emails,
            "keywords": keywords,
            "search_initiated": filters['search_initiated'], 
            "last_30_days": filters['last_30_days'],
            "last_60_days": filters['last_60_days'], 
            "conversations": grouped_emails,
            "conversations_score": conversations_score,
            "latest_timestamp": latest_timestamp,  # Include latest timestamp
            "start_date": filters['start_date'], 
            "end_date": filters['end_date'],
            "project_name": project_name
        }


    def process_projects(self, filters=None, session_email=None, session_password=None):
        if filters is None:
            filters = {
                'search_initiated': False,
                'last_30_days': True,
                'last_60_days': False,
                'subject': None,
                'content': None,
                'bidirectional_address': None,
                'start_date': None,
                'end_date': None,
                'selected_keyword': None
            }
        logging.info(f"INSIDE PROCESS EMAILS!!!")
        success, projects = knowledge_base.fetch_all_projects()
        if not success:
            logging.error(f"Error fetching projects: {projects}")
            return

        if not session_email and not session_password:
            for project in projects:
                logging.info(f"Currently processing project: {project}")
                if len(project) != 9:  # Expecting 9 fields now
                    logging.error(f"Unexpected project tuple length: {len(project)}. Data: {project}")
                    continue  # Skip processing this project
                project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, last_updated = project
                self.process_project(email_id=email_id, app_password=app_password, project_keywords=keywords_data, filters=filters,project_name=project_name)
        else:
            success, project_details = knowledge_base.get_project_details(session_email)
            if not success:
                logging.error(f"Error retrieving project information. Please check your inputs and try again.")
                return
            project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, last_updated  = project_details
            logging.info(f"Currently processing project: {project_details}")
            data = self.process_project(email_id=session_email, app_password=app_password, project_keywords=keywords_data, filters=filters, project_name=project_name)


            # Divide grouped emails by AI state
            manual_and_automated_emails = {}
            archived_emails = {}
            ai_response_states = {}
            latest_timestamp = data['latest_timestamp']


            for thread_id, email_list in data['conversations'].items():
                state_success, ai_state = knowledge_base.get_ai_response_state(thread_id)
                if not state_success:
                    # manual_and_automated_emails[thread_id] = email_list
                    # logging.info(f"This is a manually sent alert to an admin {thread_id}: {email_list}")
                    continue

                ai_response_states[thread_id] = ai_state
                if ai_state == "Archive":
                    archived_emails[thread_id] = email_list
                else:
                    manual_and_automated_emails[thread_id] = email_list
            # Extract latest timestamp for archived emails
            archived_timestamps = {thread_id: latest_timestamp[thread_id] for thread_id in archived_emails.keys() if thread_id in latest_timestamp}


            data['conversations'] = manual_and_automated_emails
            data['archived_emails'] = archived_emails  # Add archived emails to the data dictionary
            data['ai_response_state'] = ai_response_states
            session['archived_latest_timestamp'] = archived_timestamps
            session['current_project_archived_emails'] = archived_emails

            
            #logging.info(f"The manual and automated conversations are \n: {data['conversations']}")
            #logging.info(f"The archived conversations are \n: {session['current_project_archived_emails']}")

            return data

            # return render_template('index.html', emails=emails, keywords=keywords,
            #                     search_initiated=search_initiated, last_30_days=last_30_days,
            #                     last_60_days=last_60_days, conversations=grouped_emails,
            #                     conversations_score=conversations_score,
            #                     start_date=start_date, end_date=end_date)