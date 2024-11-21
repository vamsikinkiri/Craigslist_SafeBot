import re
from flask import session, flash
from knowledge_base import KnowledgeBase
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
        print('Entered into process_grouped_emails')
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
                    print(is_email_processed)
                    flash(is_email_processed)
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
                        print(seen_keywords)
                        flash(seen_keywords)
                        return
                print('seen_keywords before')
                # Calculate the cumulative score using the project keywords and seen_keywords
                seen_keywords, score = interaction_profiling.calculate_cumulative_score(
                    content, project_keywords, seen_keywords
                )
                print('seen_keywords after')

                # Update or create the thread in the database
                success, result = knowledge_base.update_email_thread(
                    thread_id, email['message_id'], score, seen_keywords
                )
                if not success:
                    print(result)
                    flash(result)
                
                # Check if the AI reponse function is enabled
                ai_success, is_ai_enabled = knowledge_base.get_ai_response_enabled(thread_id=thread_id)
                print(ai_success, is_ai_enabled)
                if not ai_success:
                    print(is_ai_enabled)
                    flash(is_ai_enabled)
                    return
                if score > 0 and is_ai_enabled[0]:
                    # AI is enabled and user is a potential criminal, we need to generate an AI response.
                    self.generate_and_send_response(email=email, conversation_history=conversation_history)

    def generate_and_send_response(self, email, conversation_history):
        # Step 1: Combine conversation history into a single string
        previous_conversations = "\n".join(conversation_history)

        # Step 2: Get the content of the current email
        email_content = email['content']

        # Step 3: Generate response using the prompt
        success, admin_prompt = knowledge_base.get_ai_prompt_text(session['email'], session['project'])
        if not success:
            print(admin_prompt)
            flash(admin_prompt)
            return
        full_prompt = (
            f"{admin_prompt[0]}\n\n"
            f"The following is a email conversation between a user (potential criminal) and an AI assistant (user doesn't know that he is having a conversation with an AI assistant):\n\n"
            f"{previous_conversations}\n\n"
            f"The last email is the latest email the user has sent. Attaching that email content alone here:\n{email_content}\n\n"
            f"Please understand the entire context and generate a reply to the latest email in a way that seems human, and showing interest in the offer but not too eager. "
            f"Only reply the content of the reply and nothing else. Start the reponse with 'Hello', and then start the content of the email. End the email with Best, Jay. Make sure the response continues the facade that you are a human buyer interested in the watches."
        )
        #print(full_prompt)
        #prompt = "You are a police detective and posted an ad saying you are looking to buy watches at a cheap price in hope of catching some criminals. You received an email as below:"
        response_text = response_generator.generate_response(full_prompt)

        # Step 4: Send the response as a reply
        to_address = email['from']
        subject = email['subject']
        references = email['references']
        email_handler.send_email(
            to_address=to_address,
            content=response_text,
            message_id=email['message_id'],
            references=references,
            subject=subject
        )

        #print("Response sent successfully.")
        return