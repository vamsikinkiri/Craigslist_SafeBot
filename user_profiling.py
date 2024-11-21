import re
import json
from knowledge_base import KnowledgeBase
import json
from collections import defaultdict
from datetime import datetime
from flask import flash

knowledge_base = KnowledgeBase()

class UserProfiling:
    def process_user_profile(self, thread_id, user_email, email_content, last_active):
        """
        Process and manage user profile information.
        Args:
            thread_id (str): The thread ID of the current conversation.
            user_email (str): The user's email address.
            email_content (str): The content of the email for extracting contact number.
        """
        # Check if user already exists in USER_PROFILES
        success, user_profile = knowledge_base.get_user_profile(user_email)
        if not success:
            print(user_profile)
            flash(user_profile, "error")
            return
        contact_number = self.extract_contact_number(email_content)
        
        if user_profile:  # User already exists
            print(user_profile)
            primary_email, thread_ids, email_list, contact_numbers, last_active_db, last_updated = user_profile
            if thread_id not in thread_ids:
                thread_ids.append(thread_id)
            if contact_number and contact_number not in contact_numbers:
                contact_numbers.append(contact_number)
                # Update the THREAD_IDS, CONTACT_NUMBER and LAST_ACTIVE
            knowledge_base.update_user_profile(user_email, thread_ids, contact_numbers, last_active)
        else: 
            # New user found. Create a new user profile
            contact_numbers = [contact_number] if contact_number else []
            knowledge_base.create_user_profile(
                user_email=user_email,
                thread_ids=[thread_id],
                email_list="",
                contact_numbers=contact_numbers,
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
        if not success:
            print("Error fetching user profiles:", all_user_profiles)
            return []

        # Return the user profiles directly
        return all_user_profiles

