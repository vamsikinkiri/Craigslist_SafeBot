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
from string import Template

knowledge_base = KnowledgeBase()
interaction_profiling = InteractionProfiling()
response_generator = ResponseGenerator()
email_handler = EmailHandler()
user_profiling = UserProfiling()
knowledge_base = KnowledgeBase()
scheduler = BackgroundScheduler()
scheduler.start()

class EmailProcessor:

    def process_grouped_emails(self, grouped_emails, session_email, project_id, project_keywords):
        for thread_id, emails in grouped_emails.items():
            conversation_history = []
            user_email = ""
            # Process each email in the thread
            for email in reversed(emails):
                # Extract sender's email for comparison
                match = re.search(r'<([^>]+)>', email['from'])
                from_address = match.group(1) if match else email['from'].strip()

                if from_address == session_email:
                    conversation_history.append(f"We replied: {email['content']}")
                    continue  # Ignore the emails the chatbot sent
                else:
                    user_email = from_address
                    conversation_history.append(f"Suspect sent: {email['content']}")

                self._process_single_email(
                    email, from_address, thread_id, session_email, project_id, project_keywords, conversation_history, len(emails)
                )
            
            # if user_email != "":
            #     user_profiling.update_user_activity_status(user_email=user_email, project_id=project_id)
            # else:
            #     logging.info(f"This is a manual trigger conversation!!")

    def _process_single_email(self, email, from_address, thread_id, session_email, project_id, project_keywords, conversation_history, email_count):
        # Check if the email is already processed
        success, is_email_processed = knowledge_base.is_email_processed(email['message_id'])
        if not success:
            logging.error(is_email_processed, "error")
            return
        if is_email_processed:
            return  # Skip already processed emails

        # Extract email content and perform profiling
        content = email['content']
        last_active = email['date'].strftime('%Y-%m-%d %H:%M:%S')
        user_profiling.process_user_profile(
            project_id=project_id,
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
            return
        
        # logging.info(f"PROJECT: {project_details}")
        # project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, lower_threshold, upper_threshold, authorized_emails, posed_name, posed_age, posed_sex, posed_location, switch_manual_criterias, project_type, last_updated, active_start, active_end  = project_details

        self._update_email_thread(email, thread_id, session_email, project_details, score, seen_keywords)
        # Determine and act on the AI response state
        self._handle_ai_response_state(email, thread_id, session_email, project_details, score, conversation_history, from_address)

    def _get_seen_keywords(self, thread_id, email_count):
        if email_count == 1:
            return {}
        success, seen_keywords = knowledge_base.get_seen_keywords(thread_id)
        if not success:
            logging.error(seen_keywords)
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
            logging.error(result)

    def _handle_ai_response_state(self, email, thread_id, session_email, project_details, score, conversation_history, from_address):
        # Extract the user profile
        user_success, user_profile = knowledge_base.get_user_profile(from_address, project_id=project_details[0])
        if not user_success:
            logging.error("Failed to fetch user profile for notification.")
            return
        user_id, primary_email, project_id, thread_ids, email_list, contact_numbers, active_user, actions_remarks, last_active_db, last_updated = user_profile
        user_details = f"""User primary Email: {primary_email}\nEmail List: {email_list if email_list else 'N/A'}\nContact Numbers: {', '.join(contact_numbers) if contact_numbers else 'N/A'}\nLast Active: {last_active_db}"""

        # Extract the AI response state
        ai_success, ai_state = knowledge_base.get_ai_response_state(thread_id)
        if not ai_success:
            logging.error(ai_state)
            return

        project_name = project_details[2]
        app_password = project_details[3]
        response_frequency = project_details[5]
        lower_threshold = project_details[8]
        upper_threshold = project_details[9]
        authorized_emails = project_details[10]
        project_type = project_details[16]

        if ai_state == 'Manual':
            # Notify all the authorized admins
            for admin_email in authorized_emails:
                self._notify_admin(project_name, admin_email, session_email, app_password, email, user_details, score, thread_id)
        elif ai_state == 'Automated' and score >= lower_threshold:
            if score < upper_threshold:
                self.schedule_or_send_reply(email, conversation_history, session_email, project_details, response_frequency, thread_id, score, user_details)
            else:
                # Notify all the authorized admins
                for admin_email in authorized_emails:
                    self._notify_admin(project_name, admin_email, session_email, app_password, email, user_details, score, thread_id, threshold_exceeded=True)
                knowledge_base.update_ai_response_state(thread_id, 'Manual')

    def _notify_admin(self, project_name, admin_email, session_email, app_password, email, user_details, score, thread_id, threshold_exceeded=False, llm_scenario_summary=None):
        if threshold_exceeded:
            action = "Manual takeover" 
            subject = f"Manual Takeover Alert: Score Exceeded Threshold ({score}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            if llm_scenario_summary is not None:
                action = "Manual switch scenario(s) matched"
                subject = f"Manual Takeover Alert: Manual switch scenario(s) matched - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                action = "Manual continuation"
                subject=f"Manual Continuation Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        notification_content = (
            f"Attention Required: {action} for project {project_name}.\n\n"
            f"User Profile:\n{user_details}\n"
            + (f"Scenarios matched:\n{llm_scenario_summary}\n" if llm_scenario_summary else "")
            + f"Interaction Score: {score}\n"
            f"Please login to the email account associated with {session_email} and continue the conversation with the subject: \"{email['subject']}\".\n\n"
            f"Best regards,\n"
            f"Craigslist SafeBot Team"
        )

        email_handler.send_notification(to_emails=admin_email, content=notification_content, subject=subject)
        # email_handler.send_email(from_address=session_email, app_password=app_password, to_address=admin_email, content=notification_content, subject=subject)
        logging.info('*'*10 + "Email sent successfully to Admin" + "*"*10)               

    def schedule_or_send_reply(self, email, conversation_history, session_email, project_details, response_frequency, thread_id, score, user_details):
        """
        Schedule or send an email reply based on response frequency, ensuring emails are sent during normal hours.
        """
        email_received_time = email['date']
        current_time = datetime.now(email_received_time.tzinfo)

        # Randomize the response frequency within ±10 minutes
        randomized_response_frequency = max(5, response_frequency + random.randint(-10, 10))
        send_time = email_received_time + timedelta(minutes=randomized_response_frequency)

        # Extract active hours to send an email
        start_hour = project_details[18]  # Default is 8 AM
        end_hour = project_details[19]   # Default is 8 PM

        if send_time.hour < start_hour:
            # If send_time is before 8 AM, move it to 8 AM on the same day
            send_time = send_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        elif send_time.hour >= end_hour:
            # If send_time is after 8 PM, move it to 8 AM on the next day
            send_time = (send_time + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)

        logging.info(f"Email received time: {email_received_time}, current time: {current_time}, send time: {send_time}, response_frequency: {randomized_response_frequency}")

        # To generate response immediately
        # self.generate_and_send_response(project_details, email, conversation_history, session_email, thread_id, score, user_details)

        if (send_time - current_time).total_seconds() <= 0:
            # If delay is negative or zero, send the reply immediately
            self.generate_and_send_response(project_details, email, conversation_history, session_email, thread_id, score, user_details)
        else:
            # Schedule the email to be sent later
            scheduler.add_job(
                func=self.generate_and_send_response,
                trigger=DateTrigger(run_date=send_time),
                args=[project_details, email, conversation_history, session_email, thread_id, score, user_details],
                id=f"send_reply_{email['message_id']}",
                replace_existing=True
            )
            logging.info(f"Scheduled reply for email {email['message_id']} at {send_time}")


    def generate_and_send_response(self, project_details, email, conversation_history, session_email, thread_id, score, user_details):
        # Verify the latest AI Response state of the Thread before sending the reply
        ai_success, ai_state = knowledge_base.get_ai_response_state(thread_id)
        if not ai_success:
            logging.error(ai_state)
            return
        if ai_state != 'Automated':
            logging.info(f"The AI Response state for the thread has been changed to Manual. No longer sending the AI generated reply to the email!")
            return

        # Step 1: Extract project details and combine conversation history into a single string
        project_name = project_details[2]
        app_password = project_details[3]
        admin_prompt = project_details[4] 
        authorized_emails = project_details[10]
        switch_manual_criterias = project_details[15]
        project_type = project_details[16]
        posed_details = self.get_posed_details(project=project_details)
        previous_conversations = "\n".join(conversation_history)

        # Step 2: Get the content of the current email, generate the prompts and call the LLM
        email_content = email['content']

        dynamic_vars = {
            "admin_prompt": admin_prompt,
            "previous_conversations": previous_conversations,
            "scenario_instructions": "\n".join(f"{i}. {criteria}" for i, criteria in enumerate(switch_manual_criterias, 1)),
            "email_content": email_content,
            "posed_details": posed_details,
        }

        success, replaced_prompts = self.get_project_type_prompts_with_dynamic_vars(project_type, dynamic_vars)
        if success:
            scenario_prompt = replaced_prompts["scenario_prompt"]
            response_prompt = replaced_prompts["response_prompt"]
        else:
            logging.error(replaced_prompts)
        
        response_text = response_generator.generate_response(scenario_prompt)
        # logging.info(f"!!!!!!!!!!!!!!!!!!!!!!!!!! LLM Evaluation Result !!!!!!!!!!!!!!!!!!!!!!!!!!:\n{response_text}")

        if "Manual Switch needs to happen" in response_text:
            # Print matching scenarios
            logging.info("One or more switch_manual_criterias matched:")
            matching_scenarios = []
            for criteria in switch_manual_criterias:
                if criteria in response_text:
                    matching_scenarios.append(criteria)

            print("Manual Switch needs to happen")
            for scenario in matching_scenarios:
                print(scenario)
            # Switch to manual mode and notify admins
            knowledge_base.update_ai_response_state(thread_id, 'Manual')
            for admin_email in authorized_emails:
                self._notify_admin(project_name, admin_email, session_email, app_password, email, user_details, score, thread_id, threshold_exceeded=False, llm_scenario_summary=matching_scenarios)
            return

        # No scenarios matched, generating a response
        response_text = response_generator.generate_response(response_prompt)
        # logging.info(f"!!!!!!!!!!!!!!!!!!!!!!!!!! LLM Evaluation Result !!!!!!!!!!!!!!!!!!!!!!!!!!:\n{response_text}")

        # Step 3: Send the response as a reply and include the original email as quoted content
        quoted_conversation = ""
        for msg in reversed(conversation_history):
            if "We replied:" in msg:
                quoted_conversation += (
                    f"On {email['date'].strftime('%a, %b %d, %Y at %I:%M %p')}, {session_email} wrote:\n"
                    f"> {msg.replace('We replied:', '').strip()}\n"
                )
            elif "Suspect sent:" in msg:
                quoted_conversation += (
                    f"On {email['date'].strftime('%a, %b %d, %Y at %I:%M %p')}, {email['from']} wrote:\n"
                    f"> {msg.replace('Suspect sent:', '').strip()}\n"
                )

        # Ensure only unique conversation history content is added to the email
        email_with_quote = (
            f"{response_text}\n\n"
            f"{quoted_conversation.strip()}"  # Strip trailing whitespace for neatness
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
        logging.info(f'*'*10 + f"Response successfully sent to {to_address}" + "*"*10)
    

    def get_project_type_prompts_with_dynamic_vars(self, project_type, dynamic_vars):
        """
        Get the prompts for a given project type and replace placeholders with dynamic variables.
        """
        success, prompts = knowledge_base.get_project_type_prompts(project_type=project_type)
        if not success:
            logging.info(prompts, "error")  # Display error message if fetching fails
            return
        try:
            base_template = Template(prompts["base_prompt"])
            scenario_template = Template(prompts["scenario_prompt"])
            response_template = Template(prompts["response_prompt"])

            # Substitute placeholders with dynamic variables
            base_prompt = base_template.safe_substitute(dynamic_vars)
            dynamic_vars['base_prompt'] = base_prompt
            replaced_prompts = {
                "scenario_prompt": scenario_template.safe_substitute(dynamic_vars),
                "response_prompt": response_template.safe_substitute(dynamic_vars),
            }
            return True, replaced_prompts
        except Exception as e:
            return False, f"Error while replacing placeholders: {e}"

    
    def get_posed_details(self, project):
        return {
            "posed_name": project[11],
            "posed_age": project[12],
            "posed_sex": project[13],
            "posed_location": project[14],
        }
    
    def switch_to_automated(self, project_details, thread_id, session_email, app_password, response_frequency, admin_prompt, lower_threshold):
        """
        Switch a conversation's state from Manual to Automated, reset its score,
        and reschedule a response if necessary.
        """
        # Step 1: Update the AI response state to 'Automated'
        success, message = knowledge_base.update_ai_response_state(thread_id, 'Automated')
        if not success:
            logging.error(f"Failed to switch AI state: {message}")
            return False, message

        # Step 2: Reset the interaction score (e.g., set it to lower_threshold)
        reset_score = lower_threshold  # We can also reduce the score by a percentage if needed
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
        # logging.info(f"Debugging the grouped emails: {grouped_emails}")
        if not success:
            # logging.error(grouped_emails)
            logging.error(f"Error fetching email by thread ID: {grouped_emails}")
            return False, grouped_emails
        
        conversation_history = []
        for email in reversed(grouped_emails): # Process emails in the order they are received
            # Extract sender's email for comparison
            match = re.search(r'<([^>]+)>', email['from'])
            from_address = match.group(1) if match else email['from'].strip()

            if from_address == session_email:
                conversation_history.append(f"We replied: {email['content']}")
                continue  # Ignore the emails the chatbot sent
            else:
                conversation_history.append(f"User sent: {email['content']}")
        
        # logging.info(f"Debugging the conversation: {conversation_history}")
        # Process the most recent email in the conversation
        latest_email = grouped_emails[0]

        if email['from'] == session_email:
            # The latest email is from the project email itself, so no need to send a reply
            # logging.info(f"Debug: {session_email}, {latest_email}")
            return True, "Successfully switched to Automated."
        
        # The latest email is from the user email
        self.schedule_or_send_reply(
            email=latest_email,
            conversation_history=conversation_history,
            session_email=session_email,
            project_details=project_details,
            response_frequency=response_frequency,
            thread_id=thread_id,
            score=reset_score,
            user_details=""
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
    
    def switch_archive_to_automated(self, thread_id):
        success, message  = knowledge_base.update_ai_response_state(thread_id, 'Automated')
        if success:
            return True, "Email thread switched from archive to automated successfully."
        else:
            return False, message
