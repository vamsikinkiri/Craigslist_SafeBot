import re
import json
import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from flask import session, flash
from knowledge_base import KnowledgeBase
from datetime import datetime, timedelta, timezone
from interaction_profiling import InteractionProfiling
from response_generator import ResponseGenerator
from email_handler import EmailHandler
from user_profiling import UserProfiling
from knowledge_base import KnowledgeBase

knowledge_base = KnowledgeBase()
interaction_profiling = InteractionProfiling()
response_generator = ResponseGenerator()
email_handler = EmailHandler()
user_profiling = UserProfiling()
knowledge_base = KnowledgeBase()
scheduler = BackgroundScheduler()
scheduler.start()

class EmailProcessor:

    def process_grouped_emails(self, grouped_emails, session_email, project_keywords):
        for thread_id, emails in grouped_emails.items():
            conversation_history = []
            # Process each email in the thread
            for email in reversed(emails):
                # Extract sender's email for comparison
                match = re.search(r'<([^>]+)>', email['from'])
                from_address = match.group(1) if match else email['from'].strip()

                if from_address == session_email:
                    conversation_history.append(f"We replied: {email['content']}")
                    continue  # Ignore the emails the chatbot sent
                else:
                    conversation_history.append(f"User sent: {email['content']}")

                self._process_single_email(
                    email, from_address, thread_id, session_email, project_keywords, conversation_history, len(emails)
                )

    def _process_single_email(self, email, from_address, thread_id, session_email, project_keywords, conversation_history, email_count):
        # Check if the email is already processed
        success, is_email_processed = knowledge_base.is_email_processed(email['message_id'])
        if not success:
            flash(is_email_processed, "error")
            return
        if is_email_processed:
            return  # Skip already processed emails

        # Extract email content and perform profiling
        content = email['content']
        last_active = email['date'].strftime('%Y-%m-%d %H:%M:%S')
        user_profiling.process_user_profile(
            thread_id=thread_id, 
            user_email=from_address, 
            email_content=content, 
            last_active=last_active
        )

        # Get seen keywords and calculate the cumulative score
        seen_keywords = self._get_seen_keywords(thread_id, email_count)
        seen_keywords, score = interaction_profiling.calculate_cumulative_score(content, project_keywords, seen_keywords)

        # Handle project details and thread update
        project_success, project_details = knowledge_base.get_project_details(session_email)
        if not project_success:
            logging.error(f"Error retrieving project information. Please check your inputs and try again.", "error")
            flash("Error retrieving project information. Please check your inputs and try again.", "error")
            return
        
        # logging.info(f"PROJECT: {project_details}")
        # project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, last_updated = project_details

        self._update_email_thread(email, thread_id, session_email, project_details, score, seen_keywords)
        # Determine and act on the AI response state
        self._handle_ai_response_state(email, thread_id, session_email, project_details, score, conversation_history, from_address)

    def _get_seen_keywords(self, thread_id, email_count):
        if email_count == 1:
            return {}
        success, seen_keywords = knowledge_base.get_seen_keywords(thread_id)
        if not success:
            flash(seen_keywords, "error")
            return {}
        return seen_keywords

    def _update_email_thread(self, email, thread_id, session_email, project_details, score, seen_keywords):
        success, result = knowledge_base.update_email_thread(
            thread_id=thread_id,
            session_email=session_email,
            session_project=project_details[2],
            message_id=email['message_id'],
            score=score,
            seen_keywords=seen_keywords
        )
        if not success:
            flash(result, "error")

    def _handle_ai_response_state(self, email, thread_id, session_email, project_details, score, conversation_history, from_address):
        # Extract the admin email
        admin_success, admin_email = knowledge_base.get_email_by_admin_id(admin_id=project_details[7])
        if not admin_success:
            logging.error(admin_email)
            flash(admin_email)
            return
        
        # Extract the user profile
        user_success, user_profile = knowledge_base.get_user_profile(from_address)
        if not user_success:
            flash("Failed to fetch user profile for notification.", "error")
            logging.error("Failed to fetch user profile for notification.")
            return
        user_id, primary_email, thread_ids, email_list, contact_numbers, last_active_db, last_updated = user_profile
        user_details = f"""User primary Email: {primary_email}\nEmail List: {email_list if email_list else 'N/A'}\nContact Numbers: {', '.join(contact_numbers) if contact_numbers else 'N/A'}\nLast Active: {last_active_db}"""

        # Extract the AI response state
        ai_success, ai_state = knowledge_base.get_ai_response_state(thread_id)
        if not ai_success:
            flash(ai_state, "error")
            return

        app_password = project_details[3]
        admin_prompt = project_details[4] 
        response_frequency = project_details[5]

        if ai_state == 'Manual':
            self._notify_admin(project_details[2], admin_email, session_email, app_password, email, user_details, score, thread_id)
        elif ai_state == 'Automated' and score > 0:
            if score < 75:
                self.schedule_or_send_reply(email, conversation_history, session_email, app_password, response_frequency, admin_prompt)
            else:
                self._notify_admin(project_details[2], admin_email, session_email, app_password, email, user_details, score, thread_id, threshold_exceeded=True)
                knowledge_base.update_ai_response_state(thread_id, 'Manual')

    def _notify_admin(self, project_name, admin_email, session_email, app_password, email, user_details, score, thread_id, threshold_exceeded=False):
        if threshold_exceeded:
            action = "Manual takeover" 
            subject = f"Manual Takeover Alert: Score Exceeded Threshold ({score}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            action = "Manual continuation"
            subject=f"Manual Continuation Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        notification_content = (
            f"Attention Required: {action} for project {project_name}.\n\n"
            f"User Profile:\n{user_details}\n"
            f"Interaction Score: {score}\n"
            f"Please login to the email account associated with {session_email} and continue the conversation with the subject: \"{email['subject']}\".\n"
        )

        email_handler.send_email(
            from_address=session_email,
            app_password=app_password,
            to_address=admin_email,
            content=notification_content,
            subject=subject
        )
        logging.info('*'*10 + "Email sent to Admin" + "*"*10)               

    def schedule_or_send_reply(self, email, conversation_history, session_email, app_password, response_frequency, admin_prompt):
        """
        Schedule or send an email reply based on response frequency, ensuring emails are sent during normal hours.
        """
        email_received_time = email['date']
        current_time = datetime.now(email_received_time.tzinfo)

        # Randomize the response frequency within ±10 minutes
        randomized_response_frequency = response_frequency + random.randint(-10, 10)
        send_time = email_received_time + timedelta(minutes=randomized_response_frequency)

        # Define acceptable send hours
        start_hour = 8  # 8 AM
        end_hour = 20   # 8 PM

        if send_time.hour < start_hour:
            # If send_time is before 8 AM, move it to 8 AM on the same day
            send_time = send_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        elif send_time.hour >= end_hour:
            # If send_time is after 8 PM, move it to 8 AM on the next day
            send_time = (send_time + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)

        logging.info(f"Email received time: {email_received_time}, current time: {current_time}, send time: {send_time}, response_frequency: {randomized_response_frequency}")

        if (send_time - current_time).total_seconds() <= 0:
            # If delay is negative or zero, send the reply immediately
            self.generate_and_send_response(email, conversation_history, session_email, app_password, admin_prompt)
        else:
            # Schedule the email to be sent later
            scheduler.add_job(
                func=self.generate_and_send_response,
                trigger=DateTrigger(run_date=send_time),
                args=[email, conversation_history, session_email, app_password],
                id=f"send_reply_{email['message_id']}",
                replace_existing=True
            )
            logging.info(f"Scheduled reply for email {email['message_id']} at {send_time}")


    def generate_and_send_response(self, email, conversation_history, session_email, app_password, admin_prompt):
        # Step 1: Combine conversation history into a single string
        previous_conversations = "\n".join(conversation_history)

        # Step 2: Get the content of the current email
        email_content = email['content']

        # Step 3: Generate response using the prompt
        full_prompt = (
            f"{admin_prompt}\n\n"
            f"The following is a email conversation between a user (potential criminal) and an AI assistant (user doesn't know that he is having a conversation with an AI assistant):\n\n"
            f"{previous_conversations}\n\n"
            f"The last email is the latest email the user has sent. Attaching that email content alone here:\n{email_content}\n\n"
            f"Please understand the entire context and generate a reply to the latest email in a way that seems human, and showing interest in the offer but not too eager. "
            f"Only reply the content of the reply and nothing else. Start the reponse with 'Hello', and then start the content of the email. End the email with Best, Jay. Make sure the response continues the facade that you are a human buyer interested in the watches."
        )
        #logging.info(full_prompt)
        #prompt = "You are a police detective and posted an ad saying you are looking to buy watches at a cheap price in the hope of catching some criminals."
        response_text = response_generator.generate_response(full_prompt)
        logging.info(response_text)
        logging.info('*'*50)

        # Step 4: Send the response as a reply and include the original email as quoted content
        quoted_conversation = ""
        for msg in reversed(conversation_history):
            if "We replied:" in msg:
                quoted_conversation += f"On {email['date'].strftime('%a, %b %d, %Y at %I:%M %p')}, you wrote:\n"
                quoted_conversation += f"> {msg.replace('We replied:', '').strip()}\n"
            elif "User sent:" in msg:
                quoted_conversation += f"On {email['date'].strftime('%a, %b %d, %Y at %I:%M %p')}, they wrote:\n"
                quoted_conversation += f"> {msg.replace('User sent:', '').strip()}\n"

        email_with_quote = (
            f"{response_text}\n\n"
            f"> On {email['date'].strftime('%a, %b %d, %Y at %I:%M %p')}, {email['from']} wrote:\n"
            f"{email['content'].strip()}"
        )

        to_address = email['from']
        subject = email['subject']
        references = email['references']
        email_handler.send_email(
            from_address=session_email,
            app_password=app_password,
            to_address=to_address,
            content=email_with_quote,
            references=references,
            message_id=email['message_id'],
            subject="Re: " + subject
        )

        #logging.info(f"Response sent successfully.")
        return
    
    def switch_to_automated(self, thread_id, session_email, app_password, response_frequency, admin_prompt):
        """
        Switch a conversation's state from Manual to Automated, reset its score,
        and reschedule a response if necessary.
        """
        # Step 1: Update the AI response state to 'Automated'
        success, message = knowledge_base.update_ai_response_state(thread_id, 'Automated')
        if not success:
            logging.error(f"Failed to switch AI state: {message}")
            return False, message

        # Step 2: Reset the interaction score (e.g., set it to 0)
        reset_score = 0  # We can also reduce the score by a percentage if needed
        success, message = knowledge_base.update_email_score(thread_id, reset_score)
        if not success:
            logging.error(f"Failed to reset email score: {message}")
            return False, message

        logging.info(f"Successfully switched thread {thread_id} to Automated and reset its score.")

        # Step 3: Fetch the latest email in the thread and reschedule
        success, grouped_emails = email_handler.fetch_email_by_thread_id(
            user=session_email, 
            password=app_password, 
            current_thread_id=thread_id
        )
        if not success:
            # logging.error(grouped_emails)
            logging.error(f"Error fetching email by thread ID: {grouped_emails}")
            return False, grouped_emails
        
        grouped_email = grouped_emails[1]
        conversation_history = []
        for email in reversed(grouped_email): # Process emails in the order they are received
            # Extract sender's email for comparison
            match = re.search(r'<([^>]+)>', email['from'])
            logging.error(f"Unexpected data structure for email: {type(email)}")
            from_address = match.group(1) if match else email['from'].strip()

            if from_address == session_email:
                conversation_history.append(f"We replied: {email['content']}")
                continue  # Ignore the emails the chatbot sent
            else:
                conversation_history.append(f"User sent: {email['content']}")

        # Process the most recent email in the conversation
        latest_email = grouped_email[0]
        self.schedule_or_send_reply(
            email=latest_email,
            conversation_history=conversation_history,
            session_email=session_email,
            app_password=app_password,
            response_frequency=response_frequency,
            admin_prompt=admin_prompt
        )

        return True, "Successfully switched to Automated and rescheduled the response."
    
    def switch_to_manual(self, thread_id):
        success, message  = knowledge_base.update_ai_response_state(thread_id, 'Manual')
        if success:
            return True, "Email thread switched to manual successfully."
        else:
            return False, message

    def switch_to_archive(self, thread_id):
        # First, verify the thread ID exists in the database
        success, ai_state = knowledge_base.get_ai_response_state(thread_id)

        if not success:
            logging.error(f"Thread ID not found: {thread_id}. Cannot archive non-existing thread.")
            return False, f"No thread found with the given thread ID."

        # Proceed to archive if it exists
        return knowledge_base.update_ai_response_state(thread_id, 'Archive')
