import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from core.config import settings

class EmailService:
    @staticmethod
    def send_email(
        recipients: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ):
        """
        Sends an email using SMTP settings from the environment.
        """
        user = settings.mail_user
        password = settings.mail_password

        if not user or not password:
            print(f"--> [MOCK EMAIL] To: {recipients} | Subject: {subject}")
            print(f"Body: {body[:100]}...")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = ", ".join(recipients)

            # Add plain-text and HTML parts
            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            # Connect and send - Try 587 (TLS) then 465 (SSL)
            try:
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
                    server.set_debuglevel(1)  # Enable debug output for Hugging Face logs
                    server.starttls()  # Secure the connection
                    server.login(user, password)
                    server.sendmail(user, recipients, msg.as_string())
                    print(f"Successfully sent email via Port {settings.SMTP_PORT}")
                    return True
            except Exception as e587:
                print(f"Port 587 failed: {e587}. Trying Port 465 (SSL)...")
                try:
                    with smtplib.SMTP_SSL(settings.SMTP_SERVER, 465, timeout=10) as server:
                        server.set_debuglevel(1)
                        server.login(user, password)
                        server.sendmail(user, recipients, msg.as_string())
                        print("Successfully sent email via Port 465 (SSL)")
                        return True
                except Exception as e465:
                    print(f"Port 465 also failed: {e465}")
                    raise e465
            
            print(f"Successfully sent email to {len(recipients)} recipients.")
            return True
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to send email: {e}")
            return False

# Global instance
email_service = EmailService()
