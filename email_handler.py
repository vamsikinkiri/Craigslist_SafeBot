import imaplib
import email
import re
import os
import re
import logging
from flask import session
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
import smtplib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.mime.base import MIMEBase
from email import encoders


class EmailHandler:
    def __init__(self):
        self.user = None
        self.password = None
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        project_root = os.path.dirname(os.path.abspath(__file__))
    
    def login_to_email(self, user, password):
        """
        Login to the IMAP email server.
        Args:
            user (str): Email address.
            password (str): App password for the email.
        Returns: imaplib.IMAP4_SSL: Authenticated IMAP connection.
        Raises:
            ValueError: If user or password is missing.
            Exception: For any other IMAP login errors.
        """
        if not user or not password:
            raise ValueError("Email or app password not provided.")
        
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')  # Replace with appropriate IMAP server
            mail.login(user, password)
            return mail
        except imaplib.IMAP4.error as e:
            logging.error(f"IMAP login failed: {e}")
            raise Exception("Failed to log in. Please check your email and app password.")
    
    def fetch_email_by_thread_id(self, user, password, current_thread_id):
        """
        Fetch conversation by a particular thread id.
        """
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
        try:
            mail = self.login_to_email(user, password)  # Reuse the login function
            mail.select('"[Gmail]/All Mail"')  # Select the All Mail folder

            search_criteria = self._build_search_criteria(filters)
            _, data = mail.search(None, search_criteria)
            _, grouped_emails, _ = self._process_email_data(mail, data)
            for thread_id, emails in grouped_emails.items():
                if thread_id == current_thread_id:
                    return True, emails
            return False, f"No conversation found for the given thread id: {current_thread_id}"

        except imaplib.IMAP4.error as e:
            logging.error(f"IMAP error during email fetching: {e}")
            raise Exception("Failed to fetch emails. Please check your filters or email server settings.")

        except Exception as e:
            logging.error(f"Unexpected error during email fetching: {e}")
            raise Exception("An unexpected error occurred while fetching emails.")

        finally:
            if mail:
                try:
                    mail.logout()
                except Exception as e:
                    logging.warning(f"Error during IMAP logout: {e}")


    def fetch_emails_and_keywords(self, user, password, **filters):
        """
        Fetch emails and keywords based on filters.
        """
        try:
            mail = self.login_to_email(user, password)  # Reuse the login function
            mail.select('"[Gmail]/All Mail"')  # Select the All Mail folder

            # Build search criteria and fetch emails
            search_criteria = self._build_search_criteria(filters)
            _, data = mail.search(None, search_criteria)
            return self._process_email_data(mail, data)
        
        except imaplib.IMAP4.error as e:
            logging.error(f"IMAP error during email fetching: {e}")
            raise Exception("Failed to fetch emails. Please check your filters or email server settings.")

        except Exception as e:
            logging.error(f"Unexpected error during email fetching: {e}")
            raise Exception("An unexpected error occurred while fetching emails.")

        finally:
            if mail:
                try:
                    mail.logout()
                except Exception as e:
                    logging.warning(f"Error during IMAP logout: {e}")

    
    def _build_search_criteria(self, filters):
        """
        Build IMAP search criteria based on filter parameters.
        """
        criteria = []
        if filters.get('bidirectional_address'):
            criteria.append(f'(OR FROM "{filters["bidirectional_address"]}" TO "{filters["bidirectional_address"]}")')
        else:
            if filters.get('from_address'):
                criteria.append(f'FROM "{filters["from_address"]}"')
            if filters.get('to_address'):
                criteria.append(f'TO "{filters["to_address"]}"')
        if filters.get('subject'):
            criteria.append(f'SUBJECT "{filters["subject"]}"')
        if filters.get('content'):
            criteria.append(f'BODY "{filters["content"]}"')
        if filters.get('start_date'):
            start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d').strftime('%d-%b-%Y')
            criteria.append(f'SINCE {start_date}')
        if filters.get('end_date'):
            end_date = (datetime.strptime(filters['end_date'], '%Y-%m-%d') + timedelta(days=1)).strftime('%d-%b-%Y')
            criteria.append(f'BEFORE {end_date}')
        return ' '.join(criteria or ['ALL'])

    
    def _process_email_data(self, mail, data):
        """
        Process email data to extract information from each message.
        """
        emails = []
        for num in data[0].split():
            _, msg_data = mail.fetch(num, '(RFC822)')
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    email_body = self._get_text_from_email(msg)
                    raw_subject = msg['subject']
                    subject = self.decode_subject(raw_subject)
                    email_date = email.utils.parsedate_to_datetime(msg['Date'])
                    if email_date and email_date.tzinfo is None:
                        email_date = email_date.replace(tzinfo=timezone.utc)  # Make offset-aware
                    emails.append({
                        "from": msg['from'],
                        "to": msg['to'],
                        "subject": subject,
                        "content": email_body,
                        "message_id": msg['Message-ID'],
                        "in_reply_to": msg.get('In-Reply-To'),
                        "references": msg.get('References', '').split(),
                        "date": email_date
                    })
        emails.sort(key=lambda x: x['date'], reverse=True)
        logging.info(f"Fetched emails: {len(emails)}")  # Debug statement
        grouped_emails = self.group_emails_by_conversation(emails)
        keywords = self.extract_keywords(emails) if emails else []
        return emails, grouped_emails, keywords
    
    def _get_text_from_email(self, msg):
        """
        Extracts and cleans the body text from an email message.
        """
        body = ""
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    body += self.clean_email_body(part.get_payload(decode=True).decode('utf-8'))
                except UnicodeDecodeError:
                    # Fallback to ISO-8859-1 or other encodings
                    body += self.clean_email_body(part.get_payload(decode=True).decode('latin1', errors='ignore'))
        return body
    
    def clean_email_body(self, email_body):
        """
        Remove quoted text (previous messages) from an email body.
        """
        if not isinstance(email_body, str):
            return ""
        # Regex pattern to match common quoted reply formats
        pattern = re.compile(
            r"(On\s+[A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}(\s+[AP]M)?\s+.*?wrote:)|"
            r"(-----Original Message-----)|"
            r"(From:\s.*?\nTo:\s.*?\nSent:\s.*?\nSubject:\s.*?\n)|"
            r"(^\s*>.*$)",  # Simplified regex to focus on the common cases
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        # Search for the pattern and truncate the email content before it
        match = pattern.search(email_body)
        if match:
            return email_body[:match.start()].strip()
        return email_body
    
    def decode_subject(self, subject):
        """
        Decode the subject into a plain string.
        """
        if not subject:
            return ""
        decoded_parts = decode_header(subject)
        subject_str = ""
        for part, encoding in decoded_parts:
            try:
                if isinstance(part, bytes):
                    subject_str += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    subject_str += part
            except (LookupError, UnicodeDecodeError):
                subject_str += part.decode('utf-8', errors='ignore') if isinstance(part, bytes) else str(part)
        return subject_str


    def group_emails_by_conversation(self, emails):
        """
        Group emails into conversation threads.
        """
        conversations = defaultdict(list)
        for email in emails:
            conversation_key = email['references'][0] if email['references'] else email['message_id']
            conversations[conversation_key].append(email)
        return conversations

    def send_email(self, from_address, app_password, to_address, content, references=None, message_id=None, subject=None, attachments=None):
        """
        Send an email reply with threading information.
        """
        # logging.info(f" '*'*50 {subject}, {references}")
        self.user = from_address
        self.password = app_password
        if not self.user or not self.password:
            raise ValueError("Email or app password not set.")
        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to_address
            msg['Subject'] = subject
            if message_id:
                msg['In-Reply-To'] = message_id
            if references is not None:
                msg['References'] = ' '.join(references + [message_id])
            msg.attach(MIMEText(content, 'plain'))
            if attachments:
                for filepath in attachments:
                    with open(filepath, 'rb') as file:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(filepath)}')
                        msg.attach(part)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            logging.info("Reply sent successfully!")
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
    
    def send_notification(self, to_emails, content, subject=None):
        """
        Send an email notification to admins.
        """
        # Flatten and normalize the list of email addresses
        if isinstance(to_emails, list):
            if any(isinstance(email, list) for email in to_emails):
                to_emails = [email for sublist in to_emails for email in sublist]
            to_emails = list(set(to_emails))  # Remove duplicates
        else:
            to_emails = [to_emails]
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        # sendgrid_api_key = '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'
        from_address = "noreplycraigslistsafebot@gmail.com"
        app_password = "iqbd sboj kknl qvbb"
        try:
            msg = MIMEMultipart()
            msg['From'] = from_address
            msg["To"] = ", ".join(to_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(content, 'plain'))
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(from_address, app_password)
                server.send_message(msg)
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
    

    def extract_keywords(self, emails):
        """
        Extract common keywords from email subjects.
        (Note: Consider moving to a different module if not used in Email Engagement)
        """
        subject_texts = [self.decode_subject(email['subject']) for email in emails]
        words = [word.lower() for subject in subject_texts for word in re.findall(r'\b\w+\b', subject)]
        return [word for word, _ in Counter(words).most_common(10) if len(word) > 3]

    

    

    


