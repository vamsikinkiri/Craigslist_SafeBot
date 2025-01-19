import re
import json
import logging
from knowledge_base import KnowledgeBase
import json
from collections import defaultdict
from datetime import datetime
from flask import flash, session

knowledge_base = KnowledgeBase()

class UserProfiling:
    def process_user_profile(self, project_id, thread_id, user_email, email_content, last_active):
        """
        Process and manage user profile information.
        Args:
            thread_id (str): The thread ID of the current conversation.
            user_email (str): The user's email address.
            email_content (str): The content of the email for extracting contact number.
        """
        # Check if user already exists in USER_PROFILES
        success, user_profile = knowledge_base.get_user_profile(user_email, project_id)
        if not success:
            logging.info(user_profile)
            flash(user_profile, "error")
            return
        contact_number = self.extract_contact_number(email_content)
        # logging.info(f"First debug log for users. For {user_email} and {project_id}: {user_profile}")
        
        if user_profile and user_profile[2]==project_id:  # User already exists in this project
            logging.info(user_profile)
            user_id, primary_email, project_id, thread_ids, email_list, contact_numbers, active_user, action_remarks,last_active_db, last_updated = user_profile
            # if thread_id not in thread_ids:
            #     thread_ids.append(thread_id)
            if contact_number and contact_number not in contact_numbers:
                contact_numbers.append(contact_number)
                # Update the THREAD_IDS, CONTACT_NUMBER and LAST_ACTIVE
            knowledge_base.update_user_profile(project_id, user_email, thread_ids, contact_numbers, active_user=True, last_active=last_active)
        else: 
            # New user found for this project. Create a new user profile
            contact_numbers = [contact_number] if contact_number else []
            knowledge_base.create_user_profile(
                user_email=user_email,
                project_id=project_id,
                thread_ids=thread_id,
                email_list="",
                contact_numbers=contact_numbers,
                active_user=True,
                action_remarks="",
                last_active=last_active,
            )

    def extract_contact_number(self, email_content):
        """
        Extract a contact number from email content using regex.
        Args: email_content (str): The content of the email.
        Returns: str: Extracted contact number or empty string if not found.
        """
        match = re.search(r'\b\d{10}\b', email_content)  # Regex for 10-digit numbers
        return match.group(0) if match else ""

    def get_all_users(self):
        success, all_user_profiles = knowledge_base.get_all_user_profiles()
        # Can include the logic to only send the active users using the active_user field in the all_user_profiles
        if not success:
            logging.error(f"Error fetching suspect profiles: {all_user_profiles}")
            return []

        # Return the suspect profiles directly
        return all_user_profiles

    def update_user_activity_status(self, user_email, project_id):
        success, last_active = knowledge_base.get_user_last_active(user_email, project_id=project_id)
        if not success:
            logging.error(f"Error fetching user's last active time: {last_active}")
            return
        current_time = datetime.now()
        days_since_last_active = (current_time - last_active).days
        logging.info(f"User: {user_email}, was last active since {days_since_last_active} days")
        if days_since_last_active > 30:
            # Mark the user as inactive since 30 days passed since the last reply from the user
            success, result = knowledge_base.update_active_user(user_email, active_user=False, project_id=project_id)
            if success:
                logging.info(f"User {user_email} marked as inactive.")
            else:
                logging.error(f"Failed to update activity for user {user_email}: {result}")

