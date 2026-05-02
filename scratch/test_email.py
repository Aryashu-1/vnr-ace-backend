import asyncio
from core.mail import email_service
from core.config import settings
import os

async def test_email():
    print("--- Configuration Debug ---")
    print(f"EMAIL_ACCOUNT from os.environ: {os.environ.get('EMAIL_ACCOUNT')}")
    print(f"SMTP_USER from settings: {settings.SMTP_USER}")
    print(f"Final mail_user: {settings.mail_user}")
    print("---------------------------")
    
    if not settings.mail_user or "@" not in settings.mail_user:
        print(f"Error: Invalid or missing email address: '{settings.mail_user}'")
        print("Please check your .env file and ensure EMAIL_ACCOUNT includes the '@' symbol (e.g., user@gmail.com)")
        return

    recipient = settings.mail_user
    subject = "VNR-ACE Email Service Test"
    body = "Congratulations! Your email automation service is now correctly configured and working."
    
    success = email_service.send_email([recipient], subject, body)
    if success:
        print(f"Success: Test email sent to {recipient}")
    else:
        print("Failure: Check your credentials or App Password.")

if __name__ == "__main__":
    asyncio.run(test_email())
