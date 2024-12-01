import logging
from datetime import datetime
from email_handler import EmailHandler
from knowledge_base import KnowledgeBase
from datetime import datetime, timedelta
from email_processor import EmailProcessor

email_handler = EmailHandler()
knowledge_base = KnowledgeBase()
email_processor = EmailProcessor()

class ProjectScheduler:

    def process_project(self, email_id, app_password, project_keywords, filters,project_name=None):
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

        # Add the score to each conversation
        conversations_score = {}
        for thread_id in grouped_emails:
            score_success, score = knowledge_base.get_interaction_score(thread_id=thread_id)
            if not score_success:
                logging.error(score_success)
                continue
            conversations_score[thread_id] = score[0] if isinstance(score, (list, tuple)) else score

        # Filter emails by selected keyword
        if filters['selected_keyword']:
            grouped_emails = {key: details for key, details in grouped_emails.items()
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
            return self.process_project(email_id=session_email, app_password=app_password, project_keywords=keywords_data, filters=filters,project_name=project_name)
                

        # return render_template('index.html', emails=emails, keywords=keywords,
        #                     search_initiated=search_initiated, last_30_days=last_30_days,
        #                     last_60_days=last_60_days, conversations=grouped_emails,
        #                     conversations_score=conversations_score,
        #                     start_date=start_date, end_date=end_date)