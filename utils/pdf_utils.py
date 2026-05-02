from io import BytesIO
from typing import Any, Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_resume_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generates a professional PDF from structured resume JSON data using ReportLab.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    name_style = ParagraphStyle(
        'NameStyle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        alignment=1, # Center
        spaceAfter=10
    )
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2563eb"), # Professional Blue
        spaceBefore=15,
        spaceAfter=5,
        borderPadding=(0, 0, 1, 0),
        borderWidth=1,
        borderColor=colors.lightgrey
    )
    normal_style = styles['Normal']
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        leftIndent=20,
        firstLineIndent=0,
        spaceBefore=3
    )

    elements = []

    # Personal Info
    personal = data.get("personal_info", {})
    elements.append(Paragraph(personal.get("name", "Name"), name_style))
    
    contact_info = []
    if personal.get("email"): contact_info.append(personal.get("email"))
    if personal.get("phone"): contact_info.append(personal.get("phone"))
    
    elements.append(Paragraph(" | ".join(contact_info), styles['Normal'], alignment=1))
    
    links = personal.get("links", [])
    if links:
        elements.append(Paragraph(" | ".join(links), styles['Normal'], alignment=1))
    
    elements.append(Spacer(1, 10))

    # Education
    education = data.get("education", [])
    if education:
        elements.append(Paragraph("EDUCATION", section_header_style))
        for edu in education:
            elements.append(Paragraph(f"<b>{edu.get('institution', 'Institution')}</b>", normal_style))
            elements.append(Paragraph(f"{edu.get('degree', 'Degree')} | {edu.get('year', 'Year')} | GPA: {edu.get('gpa', 'N/A')}", normal_style))
            elements.append(Spacer(1, 5))

    # Skills
    skills = data.get("skills", [])
    if skills:
        elements.append(Paragraph("TECHNICAL SKILLS", section_header_style))
        if isinstance(skills, list):
            if all(isinstance(s, str) for s in skills):
                elements.append(Paragraph(", ".join(skills), normal_style))
            else:
                for s in skills:
                    if isinstance(s, dict):
                        cat = s.get("category", "Skills")
                        items = s.get("items", [])
                        elements.append(Paragraph(f"<b>{cat}:</b> {', '.join(items)}", normal_style))
        elements.append(Spacer(1, 5))

    # Experience
    experience = data.get("experience", [])
    if experience:
        elements.append(Paragraph("EXPERIENCE", section_header_style))
        for exp in experience:
            elements.append(Paragraph(f"<b>{exp.get('role', 'Role')}</b> | {exp.get('company', 'Company')}", normal_style))
            elements.append(Paragraph(f"<i>{exp.get('duration', 'Duration')}</i>", normal_style))
            desc = exp.get("description", "")
            if isinstance(desc, str):
                for bullet in desc.split('\n'):
                    if bullet.strip():
                        elements.append(Paragraph(f"• {bullet.strip()}", bullet_style))
            elif isinstance(desc, list):
                for bullet in desc:
                    elements.append(Paragraph(f"• {bullet}", bullet_style))
            elements.append(Spacer(1, 5))

    # Projects
    projects = data.get("projects", [])
    if projects:
        elements.append(Paragraph("PROJECTS", section_header_style))
        for proj in projects:
            elements.append(Paragraph(f"<b>{proj.get('title', 'Project')}</b>", normal_style))
            desc = proj.get("description", "")
            if isinstance(desc, str):
                for bullet in desc.split('\n'):
                    if bullet.strip():
                        elements.append(Paragraph(f"• {bullet.strip()}", bullet_style))
            elif isinstance(desc, list):
                for bullet in desc:
                    elements.append(Paragraph(f"• {bullet}", bullet_style))
            elements.append(Spacer(1, 5))

    # Achievements
    achievements = data.get("achievements", [])
    if achievements:
        elements.append(Paragraph("ACHIEVEMENTS", section_header_style))
        for ach in achievements:
            elements.append(Paragraph(f"• {ach}", bullet_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
