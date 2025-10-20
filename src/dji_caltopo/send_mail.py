import smtplib
from email.message import EmailMessage
import logging

logger = logging.getLogger("send_mail")

def send_email(to_email, subject, body_text, from_email, app_password):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body_text)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(from_email, app_password)
            smtp.send_message(msg)
            logger.info(f"✅ Email sent successfully to {to_email}.")           
    except Exception as e:
        print(f"❌ Failed to send email: {e}")