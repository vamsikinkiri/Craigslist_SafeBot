import re
import json
from flask import session, flash
from knowledge_base import KnowledgeBase
from datetime import datetime
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

class EmailProcessor:

    def process_grouped_emails(self, grouped_emails):
        for thread_id, emails in grouped_emails.items():
            conversation_history = []
            for email in reversed(emails): # Process emails in the order they are received
                # Extract sender's email for comparison
                match = re.search(r'<([^>]+)>', email['from'])
                from_address = match.group(1) if match else email['from'].strip()

                if from_address == session['email']:
                    conversation_history.append(f"We replied: {email['content']}")
                    continue  # Ignore the emails the chatbot sent
                else:
                    conversation_history.append(f"User sent: {email['content']}")

                # Check if the email has already been scored
                success, is_email_processed = knowledge_base.is_email_processed(email['message_id'])
                if not success:
                    flash(is_email_processed, "error")
                    return
                if is_email_processed:
                    continue  # Skip since we already scored this email

                # Start processing the email. Fist, extract content, date and project keywords.
                content = email['content']
                project_keywords = session.get('project_keywords', {})
                last_active = email['date'].strftime('%Y-%m-%d %H:%M:%S')

                # Perform the User Profiling
                user_profiling.process_user_profile(thread_id=thread_id, user_email=from_address, email_content=content, last_active=last_active)

                # Determine seen_keywords for the thread
                if len(emails) == 1:
                    # New conversation. So seen_keywords so far will be empty.
                    seen_keywords = {}
                else:
                    # This email is a reply to an AI response and so seen_keywords so far needs to be extracted.
                    success, seen_keywords = knowledge_base.get_seen_keywords(thread_id)
                    if not success:
                        flash(seen_keywords, "error")
                        return
                # Calculate the cumulative score using the project keywords and seen_keywords
                seen_keywords, score = interaction_profiling.calculate_cumulative_score(
                    content, project_keywords, seen_keywords
                )

                # Update or create the thread in the database
                success, result = knowledge_base.update_email_thread(
                    thread_id, email['message_id'], score, seen_keywords
                )
                if not success:
                    flash(result, "error")
                
                # Check if the AI reponse function is enabled
                ai_success, is_ai_enabled = knowledge_base.get_ai_response_enabled(thread_id=thread_id)
                if not ai_success:
                    flash(is_ai_enabled, "error")
                    return
                if score > 0 and is_ai_enabled[0]:
                    # AI is enabled and user is a potential criminal, we need to generate an AI response.
                    if score >= 75:
                        admin_email = session.get('admin_email')
                        success, user_profile = knowledge_base.get_user_profile(from_address)
                        user_id, primary_email, thread_ids, email_list, contact_numbers, last_active_db, last_updated = user_profile
                        user_details = f"""Primary Email: {primary_email}\nEmail List: {email_list if email_list else 'N/A'}\nContact Numbers: {', '.join(contact_numbers) if contact_numbers else 'N/A'}\nLast Active: {last_active_db}"""
                        if success:
                            # Extract user profile details
                            #user_details = json.dumps(user_profile, indent=2)  # Format user profile for readability
                            notification_content = (
                                f"Attention Required: A manual takeover is suggested.\n\n"
                                f"User Profile:\n{user_details}\n"
                                f"Interaction Score: {score}\n"
                                f"Thread ID: {str(thread_id)}\n\n"
                                f"Please investigate further."
                            )
                            email_handler.send_email(
                                to_address=admin_email,
                                content=notification_content,
                                subject=f"Manual Takeover Alert: Score Exceeded Threshold ({score}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                            knowledge_base.update_ai_response_enabled(thread_id=thread_id, new_value=False)
                        else:
                            flash("Failed to fetch user profile for notification.", "error")
                    else:
                        self.generate_and_send_response(email=email, conversation_history=conversation_history)

    def generate_and_send_response(self, email, conversation_history):
        # Step 1: Combine conversation history into a single string
        previous_conversations = "\n".join(conversation_history)

        # Step 2: Get the content of the current email
        email_content = email['content']

        # Step 3: Generate response using the prompt
        success, project_details = knowledge_base.get_project_details(session['email'])
        if not success:
            flash(admin_prompt, "error")
        #print("PROJECT: ", project_details)
        _, _, _, _, admin_prompt, _, _, _ = project_details
        full_prompt = (
            f"{admin_prompt}\n\n"
            f"The following is a email conversation between a user (potential criminal) and an AI assistant (user doesn't know that he is having a conversation with an AI assistant):\n\n"
            f"{previous_conversations}\n\n"
            f"The last email is the latest email the user has sent. Attaching that email content alone here:\n{email_content}\n\n"
            f"Please understand the entire context and generate a reply to the latest email in a way that seems human, and showing interest in the offer but not too eager. "
            f"Only reply the content of the reply and nothing else. Start the reponse with 'Hello', and then start the content of the email. End the email with Best, Jay. Make sure the response continues the facade that you are a human buyer interested in the watches."
        )
        #print(full_prompt)
        #prompt = "You are a police detective and posted an ad saying you are looking to buy watches at a cheap price in hope of catching some criminals. You received an email as below:"
        response_text = response_generator.generate_response(full_prompt)
        print(response_text)
        print('*'*50)

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
            to_address=to_address,
            content=email_with_quote,
            references=references,
            message_id=email['message_id'],
            subject="Re: " + subject
        )

        #print("Response sent successfully.")
        return