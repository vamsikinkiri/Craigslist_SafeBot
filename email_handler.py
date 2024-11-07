import imaplib
import email
import yaml
import re
import os
import re
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailHandler:
    def __init__(self):
        project_root = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(project_root, "credentials.yaml")
        with open(credentials_path) as f:
            self.credentials = yaml.load(f, Loader=yaml.FullLoader)

    def fetch_emails(self, **filters):
        """
        Fetch emails based on various filters.
        """
        user, password = self.credentials["user"], self.credentials["password"]
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(user, password)
        mail.select('"[Gmail]/All Mail"')

        search_criteria = self._build_search_criteria(filters)
        _, data = mail.search(None, search_criteria)
        return self._process_email_data(mail, data)

    def group_emails_by_conversation(self, emails):
        """
        Group emails into conversation threads.
        """
        conversations = defaultdict(list)
        for email in emails:
            conversation_key = email['references'][0] if email['references'] else email['message_id']
            conversations[conversation_key].append(email)
        return conversations

    def send_email(self, to_address, content, message_id, references, subject=None):
        """
        Send an email reply with threading information.
        """
        smtp_config = self.credentials['smtp']
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_config['smtp_user']
            msg['To'] = to_address
            msg['Subject'] = "Re: " + subject
            msg['In-Reply-To'] = message_id
            msg['References'] = ' '.join(references + [message_id])
            msg.attach(MIMEText(content, 'plain'))

            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                server.starttls()
                server.login(smtp_config['smtp_user'], smtp_config['smtp_password'])
                server.send_message(msg)
        except Exception as e:
            print("Failed to send email:", e)

    def extract_keywords(self, emails):
        """
        Extract common keywords from email subjects.
        (Note: Consider moving to a different module if not used in Email Engagement)
        """
        subject_texts = [email['subject'] for email in emails]
        words = [word.lower() for subject in subject_texts for word in re.findall(r'\b\w+\b', subject)]
        return [word for word, _ in Counter(words).most_common(10) if len(word) > 3]

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
                    emails.append({
                        "from": msg['from'],
                        "to": msg['to'],
                        "subject": msg['subject'],
                        "content": email_body,
                        "message_id": msg['Message-ID'],
                        "in_reply_to": msg.get('In-Reply-To'),
                        "references": msg.get('References', '').split(),
                        "date": email.utils.parsedate_to_datetime(msg['Date'])
                    })
        emails.sort(key=lambda x: x['date'], reverse=True)
        print(f"Fetched emails: {len(emails)}")  # Debug statement
        #print(emails)
        return emails

    def _get_text_from_email(self, msg):
        """
        Extracts and cleans the body text from an email message.
        """
        body = ""
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body += self.clean_email_body(part.get_payload(decode=True).decode())
        return body  

    def clean_email_body(self, email_body):
        """
        Remove quoted text (previous messages) from an email body.
        """
        # Regex pattern to match common quoted reply formats
        pattern = re.compile(
            r"(On\s+[A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}(\s+[AP]M)?\s+.*?wrote:)|"
            r"(-----Original Message-----)|"
            r"(From:\s.*?\nTo:\s.*?\nSent:\s.*?\nSubject:\s.*?\n)|"
            r"(^\s*>.*$)|"  # Lines starting with '>' (common in plain-text replies)
            r"(On\s+\S+\s+\S+\s+.*\s+wrote:)|"
            r"(On\s+[A-Za-z]+\s+\d{1,2}(\,\s+\d{4})?\s+at\s+\d{1,2}:\d{2}\s+[AP]M\s+[A-Za-z]+\s+[<].*?@[A-Za-z]+\.[A-Za-z]+[>]\s+wrote:)",
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )
        
        # Search for the pattern and truncate the email content before it
        match = pattern.search(email_body)
        if match:
            return email_body[:match.start()].strip()
        return email_body


