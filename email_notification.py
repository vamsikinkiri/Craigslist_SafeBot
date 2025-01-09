import os
import sendgrid
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SendGrid Email Notification
def send_email_notification(to_emails, project_name):
    if any(isinstance(email, list) for email in to_emails):
        to_emails = [email for sublist in to_emails for email in sublist]
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    APP_PASSWORD = "iqbd sboj kknl qvbb"
    # sendgrid_api_key = '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'
    FROM_EMAIL = "noreplycraigslistsafebot@gmail.com"
    subject = f"Notification: Added to Project '{project_name}'"
    body = (
    f"Hello,\n\n"
    f"You have been added as an authorized user to the project: {project_name}.\n\n"
    f"This is an automated message from Craigslist Safebot. "
    f"Please do not reply to this email as responses are not monitored.\n\n"
    f"If you have any questions, contact the admin directly.\n\n"
    f"Best regards,\n"
    f"Craigslist Safebot"
    )

    # Create a MIME email message
    message = MIMEMultipart()
    message["From"] = FROM_EMAIL
    message["To"] = ", ".join(to_emails)
    message["Subject"] = subject

    # Add body to the email
    message.attach(MIMEText(body, "plain"))

    try:
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Start TLS encryption
        server.login(FROM_EMAIL, APP_PASSWORD)  # Login using app password

        # Send the email
        server.sendmail(FROM_EMAIL, to_emails, message.as_string())
        print(f"Email successfully sent to {to_emails}")

    except Exception as e:
        print(f"Failed to send email: {e}")

    finally:
        # Close the SMTP server connection
        server.quit()
