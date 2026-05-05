import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger('alert_system', 'alerts.log')
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

class AlertNotifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        self.alert_phone = os.getenv("ALERT_PHONE_NUMBER")
        
        # Initialize Twilio Client (will fail gracefully later if mock credentials are used)
        try:
            self.twilio_client = Client(self.twilio_sid, self.twilio_token)
        except Exception as e:
            logger.warning(f"Failed to initialize Twilio client (using mock?): {e}")
            self.twilio_client = None

    def send_email_alert(self, username, activity_type, risk_score):
        if not self.sender_email or not self.sender_password or self.sender_email == 'your_email@gmail.com':
            logger.warning("Email credentials not configured properly. Skipping email alert.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.sender_email # Send to admin/self for now
            msg['Subject'] = f"SicherungX HIGH RISK ALERT: {username}"

            body = f"""
            SicherungX DLP Alert
            ---------------------
            User: {username}
            Activity: {activity_type}
            Risk Score: {risk_score}/100
            
            Immediate attention is required. Please check the dashboard.
            """
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent successfully for user {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def send_sms_alert(self, username, activity_type, risk_score):
        if not self.twilio_client or self.twilio_sid == 'mock_sid':
            logger.warning("Twilio credentials not configured. Skipping SMS alert (Mock Mode).")
            # We mock the successful send if it's mock
            logger.info(f"[MOCK] SMS Sent to {self.alert_phone}: High risk activity by {username}.")
            return True

        try:
            message = self.twilio_client.messages.create(
                body=f"SicherungX Alert: {username} performed {activity_type}. Risk: {risk_score}",
                from_=self.twilio_phone,
                to=self.alert_phone
            )
            logger.info(f"SMS alert sent successfully: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            return False

    def send_alert(self, username, activity_type, risk_score):
        """Dispatches both email and SMS alerts for a high-risk event."""
        logger.warning(f"Triggering alerts for user {username}. Risk Score: {risk_score}")
        
        email_sent = self.send_email_alert(username, activity_type, risk_score)
        sms_sent = self.send_sms_alert(username, activity_type, risk_score)
        
        return email_sent or sms_sent

if __name__ == "__main__":
    # Test alert system
    notifier = AlertNotifier()
    notifier.send_alert("test_user", "Mass File Access", 85.5)
