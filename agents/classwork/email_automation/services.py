# agents/classwork/mail_automation/services.py
from core.mail import email_service

class LLMService:
    def invoke_structured(self, system_prompt, user_prompt, schema):
        raise NotImplementedError

class EmailService:
    def send_email(self, recipients, subject, body):
        """
        Sends email using the core email service.
        """
        return email_service.send_email(recipients, subject, body)

class AuditRepo:
    def persist(self, events):
        pass