from typing import Literal, TypedDict, List, Dict, Any, Optional
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from core.llm import groq_llm
from sqlalchemy.future import select
from core.db import get_db
from models.job_notification import JobNotification
from models.student import Student
from models.company import Company
from models.placement import Placement
import os
import imaplib
import email
from email.header import decode_header
import json
from bs4 import BeautifulSoup
import asyncio

def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def fetch_unread_emails_sync():
    email_user = os.getenv("EMAIL_ACCOUNT")
    email_pass = os.getenv("EMAIL_PASSWORD")
    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")

    if not email_user or not email_pass:
        return json.dumps([{"error": "EMAIL_ACCOUNT or EMAIL_PASSWORD not set in environment variables."}])

    try:
        # Connect to the server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_user, email_pass)
        
        # Select the inbox
        mail.select("inbox")

        # Search for all unread emails
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            mail.logout()
            return "[]" # No new emails

        email_list = []
        for match in messages[0].split():
            # Fetch the email data
            res, msg_data = mail.fetch(match, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Parse a bytes email into a message object
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                        
                    # Decode sender
                    sender = msg.get("From")
                    
                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body += part.get_payload(decode=True).decode(errors="ignore")
                            elif content_type == "text/html" and "attachment" not in content_disposition:
                                # Fallback to HTML if no plain text
                                html_content = part.get_payload(decode=True).decode(errors="ignore")
                                body += clean_html(html_content)
                                
                            # Basic Attachment check
                            if "attachment" in content_disposition:
                                filename = part.get_filename()
                                body += f"\n[Attachment found: {filename}] "
                    else:
                        content_type = msg.get_content_type()
                        payload = msg.get_payload(decode=True).decode(errors="ignore")
                        if content_type == "text/html":
                            body = clean_html(payload)
                        else:
                            body = payload

                    email_list.append({
                        "id": match.decode(),
                        "subject": subject,
                        "sender": sender,
                        "body": body[:2000] # truncate to avoid token limits
                    })
                    
        mail.logout()
        return json.dumps(email_list)
        
    except Exception as e:
        return json.dumps([{"error": str(e)}])

@tool
async def read_inbox_tool() -> str:
    """
    Reads the latest UNREAD emails from the placement inbox.
    Returns a JSON string containing a list of recent emails.
    Requires EMAIL_ACCOUNT and EMAIL_PASSWORD environment variables.
    """
    print("[Agent] Checking for new emails...")
    return await asyncio.to_thread(fetch_unread_emails_sync)

@tool
async def add_job_notification_tool(
    company_name: str, 
    role: str, 
    description: str, 
    min_cgpa: float, 
    allowed_branches: List[str]
) -> str:
    """
    Adds a new job notification to the database.
    Always call this when a job notification is discovered in the inbox.
    """
    async for session in get_db():
        new_job = JobNotification(
            company_name=company_name,
            role=role,
            description=description,
            min_cgpa=min_cgpa,
            allowed_branches=allowed_branches
        )
        session.add(new_job)
        await session.commit()
        return f"Successfully saved Job Notification for {role} at {company_name}."
    return "Error: Could not connect to DB."

@tool
async def shortlist_and_email_students_tool(company_name: str, role: str, min_cgpa: float, allowed_branches: List[str]) -> str:
    """
    Shortlists students based on criteria and sends them an email about the new job.
    """
    async for session in get_db():
        # Query matching students
        stmt = select(Student).where(Student.cgpa >= min_cgpa).where(Student.branch.in_(allowed_branches))
        result = await session.execute(stmt)
        students = result.scalars().all()
        
        count = len(students)
        # Mock sending email
        print(f"--> [MOCK EMAIL] Sent notification to {count} students for {company_name} - {role}.")
        
        return f"Shortlisted and emailed {count} eligible students for {company_name} - {role}."
    return "Error: Could not connect to DB."

@tool
async def update_placement_results_tool(company_name: str, roll_numbers: List[str], ctc_lpa: float) -> str:
    """
    Updates the database with missing placement results.
    Provide the company name and list of selected student roll numbers.
    """
    async for session in get_db():
        # Get or create company
        stmt_company = select(Company).where(Company.name == company_name)
        result_company = await session.execute(stmt_company)
        company = result_company.scalars().first()
        
        if not company:
            company = Company(name=company_name)
            session.add(company)
            await session.commit()
            await session.refresh(company)

        # Get students and add placements
        success_count = 0
        for roll_no in roll_numbers:
            stmt_student = select(Student).where(Student.roll_no == roll_no)
            res_student = await session.execute(stmt_student)
            student = res_student.scalars().first()
            if student:
                # Add placement record
                placement = Placement(
                    student_id=student.id,
                    company_id=company.id,
                    ctc_lpa=ctc_lpa
                )
                session.add(placement)
                success_count += 1
                
        await session.commit()
        return f"Successfully updated placement results for {success_count} students at {company_name}."
    return "Error: Could not connect to DB."

# ==========================================
# 2. Build ReAct Graph
# ==========================================

tools = [
    read_inbox_tool,
    add_job_notification_tool,
    shortlist_and_email_students_tool,
    update_placement_results_tool
]

system_prompt = """You are the autonomous Training & Placement (T&P) Admin Agent.
Your job is to manage the placement process autonomously by reading emails and taking corresponding actions.
When executed, you MUST:
1. Always start by reading the inbox using `read_inbox_tool`.
2. For ANY job notification email: 
    a) Extract the details and use `add_job_notification_tool` to save it to the database.
    b) Then, use `shortlist_and_email_students_tool` with the same criteria to notify eligible students.
3. For ANY placement results email:
    a) Extract the company name, list of roll numbers, and CTC.
    b) Use `update_placement_results_tool` to record their success.

Once you have processed all emails, summarize the actions you took and finish.
"""

# Initialize the LLM
llm = groq_llm

# Create the agent using LangGraph's prebuilt ReAct agent
tp_admin_agent = create_react_agent(llm, tools, prompt=system_prompt)
