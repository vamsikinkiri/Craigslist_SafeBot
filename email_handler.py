import imaplib
import email
import re
import os
import re
from flask import session
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header


class EmailHandler:
    def __init__(self):
        self.user = None
        self.password = None
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        project_root = os.path.dirname(os.path.abspath(__file__))

    def fetch_emails_and_keywords(self, **filters):
        """
        Fetch emails based on various filters.
        """
        self.user = session.get('email')  # Get the session email
        self.password = session.get('app_password')  # Get the session app password
        if not self.user or not self.password:
            raise ValueError("Session email or app password not set.")
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(self.user, self.password)
        mail.select('"[Gmail]/All Mail"')

        search_criteria = self._build_search_criteria(filters)
        _, data = mail.search(None, search_criteria)
        return self._process_email_data(mail, data)
    
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
                    subject = self._decode_subject(raw_subject)
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
        print(f"Fetched emails: {len(emails)}")  # Debug statement
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
    
    def _decode_subject(self, raw_subject):
        """
        Decode email subject into a plain string.
        """
        if not raw_subject:
            return ""
        decoded_parts = decode_header(raw_subject)
        subject = ""
        for part, encoding in decoded_parts:
            try:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    subject += part
            except Exception:
                subject += "[Undecodable Subject]"
        return subject

    def group_emails_by_conversation(self, emails):
        """
        Group emails into conversation threads.
        """
        conversations = defaultdict(list)
        for email in emails:
            conversation_key = email['references'][0] if email['references'] else email['message_id']
            conversations[conversation_key].append(email)
        return conversations

    def send_email(self, to_address, content, message_id=None, references=None, subject=None):
        """
        Send an email reply with threading information.
        """
        print('*'*50 + subject)
        self.user = session.get('email')  # Get the session email
        self.password = session.get('app_password')  # Get the session app password
        if not self.user or not self.password:
            raise ValueError("Session email or app password not set.")
        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to_address
            msg['Subject'] = subject
            if message_id:
                msg['In-Reply-To'] = message_id
            if references:
                msg['References'] = ' '.join(references + [message_id])
            msg.attach(MIMEText(content, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
        except Exception as e:
            print("Failed to send email:", e)

    def extract_keywords(self, emails):
        """
        Extract common keywords from email subjects.
        (Note: Consider moving to a different module if not used in Email Engagement)
        """
        def decode_subject(subject):
            """
            Decode the subject into a plain string.
            """
            if subject:
                decoded_parts = decode_header(subject)
                subject_str = ""
                for part, encoding in decoded_parts:
                    try:
                        # Handle bytes and decode them with the detected or default encoding
                        if isinstance(part, bytes):
                            if encoding in (None, 'unknown-8bit'):
                                # Assume UTF-8 for unknown or missing encodings
                                subject_str += part.decode('utf-8', errors='ignore')
                            else:
                                subject_str += part.decode(encoding, errors='ignore')
                        else:
                            # If part is already a string, append it directly
                            subject_str += part
                    except (LookupError, UnicodeDecodeError):
                        # Fallback to UTF-8 if decoding fails
                        subject_str += part.decode('utf-8', errors='ignore') if isinstance(part, bytes) else str(part)
                return subject_str
            return ""
        subject_texts = [decode_subject(email['subject']) for email in emails]
        words = [word.lower() for subject in subject_texts for word in re.findall(r'\b\w+\b', subject)]
        return [word for word, _ in Counter(words).most_common(10) if len(word) > 3]

    
    

    
    
    

    


