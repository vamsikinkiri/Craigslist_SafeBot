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
            for email in reversed(emails): # Process emails in the order they are received
                # Extract sender's email for comparison
                match = re.search(r'<([^>]+)>', email['from'])
                from_address = match.group(1) if match else email['from'].strip()

                if from_address == session_email:
                    conversation_history.append(f"We replied: {email['content']}")
                    continue  # Ignore the emails the chatbot sent
                else:
                    conversation_history.append(f"User sent: {email['content']}")

                # Check if the email has already been processed (scored)
                success, is_email_processed = knowledge_base.is_email_processed(email['message_id'])
                if not success:
                    flash(is_email_processed, "error")
                    return
                if is_email_processed:
                    continue  # Skip since we already processed this email

                # Start processing the email. Fist, extract content, date and project keywords.
                content = email['content']
                last_active = email['date'].strftime('%Y-%m-%d %H:%M:%S')

                # Perform the User Profiling
                user_profiling.process_user_profile(thread_id=thread_id, user_email=from_address, email_content=content, last_active=last_active)

                # Determine seen_keywords for the thread
                if len(emails) == 1:
                    # New conversation. So seen_keywords so far will be empty.
                    seen_keywords = {}
                else:
                    # This email is a reply to an AI response and so seen_keywords so far needs to be extracted.
                    keywords_success, seen_keywords = knowledge_base.get_seen_keywords(thread_id)
                    if not keywords_success:
                        flash(seen_keywords, "error")
                        return
                    
                # Calculate the cumulative score using the project keywords and seen_keywords
                seen_keywords, score = interaction_profiling.calculate_cumulative_score(content, project_keywords, seen_keywords)
                
                project_success, project_details = knowledge_base.get_project_details(session_email)
                if not project_success:
                    logging.error(f"Error retrieving project information. Please check your inputs and try again.", "error")
                    flash("Error retrieving project information. Please check your inputs and try again.", "error")
                    return
                #logging.info(f"PROJECT: {project_details}")
                project_id, email_id, project_name, app_password, ai_prompt_text, response_frequency, keywords_data, owner_admin_id, last_updated = project_details

                # Update or create the thread in the database
                success, result = knowledge_base.update_email_thread(
                    thread_id, 
                    session_email=session_email, 
                    session_project=project_name, 
                    message_id=email['message_id'], 
                    score=score, 
                    seen_keywords=seen_keywords
                )
                if not success:
                    flash(result, "error")    
        
                # Extract the admin email and user profile
                admin_success, admin_email = knowledge_base.get_email_by_admin_id(admin_id=owner_admin_id)
                if not admin_success:
                    logging.error(admin_email)
                    flash(admin_email)
                    return
                
                user_success, user_profile = knowledge_base.get_user_profile(from_address)
                if not user_success:
                    flash("Failed to fetch user profile for notification.", "error")
                    logging.error("Failed to fetch user profile for notification.")
                    return
                user_id, primary_email, thread_ids, email_list, contact_numbers, last_active_db, last_updated = user_profile
                user_details = f"""User primary Email: {primary_email}\nEmail List: {email_list if email_list else 'N/A'}\nContact Numbers: {', '.join(contact_numbers) if contact_numbers else 'N/A'}\nLast Active: {last_active_db}"""

                # Check which state the conversation is and act accordingly
                ai_success, ai_state = knowledge_base.get_ai_response_state(thread_id=thread_id)
                if not ai_success:
                    flash(ai_state, "error")
                    return
                
                if ai_state == 'Manual':
                    # Notify admin for continuing the manual conversation
                    notification_content = (
                        f"Attention Required: Manual continuation for project {project_name}.\n\n"
                        f"User Profile:\n{user_details}\n"
                        f"Interaction Score: {score}\n"
                        #f"Thread ID: {str(thread_id)}\n\n"
                        f"Please login to the email account associated with {session_email} and continue the manual conversation with the subject: \"{email['subject']}\".\n\n"
                    )

                    # Send notification email to admin
                    email_handler.send_email(
                        from_address=session_email,
                        app_password=app_password,
                        to_address=admin_email,
                        content=notification_content,
                        subject=f"Manual Continuation Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    logging.info('*'*50 + "SENT EMAIL TO ADMIN FOR MANUAL CONTINUATION" + '*'*50)

                elif ai_state == 'Automated' and score > 0:
                    # AI is enabled and user is a potential criminal, need to generate an AI response.
                    if score < 75:
                        # Continue the conversation by sending an AI generated response
                        self.schedule_or_send_reply(
                            email=email, 
                            conversation_history=conversation_history, 
                            session_email=session_email, 
                            app_password=app_password, 
                            response_frequency=response_frequency)
                    else:
                        # The score crossed the threshold, notify the admin via email and update the current response state of the thread to Manual
                        notification_content = (
                            f"Attention Required: Manual takeover for project {project_name}.\n\n"
                            f"User Profile:\n{user_details}\n"
                            f"Interaction Score: {score}\n"
                            #f"Thread ID: {str(thread_id)}\n\n"
                            f"Please login to the email account associated with {session_email} and takeover the conversation with the subject: \"{email['subject']}\".\n\n"
                        )

                        email_handler.send_email(
                            from_address=session_email,
                            app_password=app_password,
                            to_address=admin_email,
                            content=notification_content,
                            subject=f"Manual Takeover Alert: Score Exceeded Threshold ({score}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        logging.info('*'*50 + "SENT EMAIL TO ADMIN" + '*'*50)
                        knowledge_base.update_ai_response_state(thread_id=thread_id, new_state='Manual')
                        

    def schedule_or_send_reply(self, email, conversation_history, session_email, app_password, response_frequency):
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
            self.generate_and_send_response(email, conversation_history, session_email, app_password)
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


    def generate_and_send_response(self, email, conversation_history, session_email, app_password):
        # Step 1: Combine conversation history into a single string
        previous_conversations = "\n".join(conversation_history)

        # Step 2: Get the content of the current email
        email_content = email['content']

        # Step 3: Generate response using the prompt
        success, project_details = knowledge_base.get_project_details(session_email)
        if not success:
            logging.error(project_details)
            flash(project_details, "error")
        #logging.info(f"PROJECT: {project_details}")
        _, _, _, _, admin_prompt, _, _, _ = project_details
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