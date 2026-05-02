import asyncio
import json
from uuid import uuid4
from agents.placements.resume_editor.latex_generator import generate_latex_resume
from agents.placements.resume_editor.utils import normalize_resume_json

def test_latex_generator():
    print("Testing LaTeX Generator...")
    sample_data = {
        "personal_info": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+91 9876543210",
            "links": ["https://linkedin.com/in/johndoe", "https://github.com/johndoe"]
        },
        "education": [
            {
                "institution": "VNR Vignana Jyothi Institute of Engineering and Technology",
                "degree": "B.Tech in Computer Science",
                "year": "2020 - 2024",
                "gpa": "9.2/10"
            }
        ],
        "skills": ["Python", "JavaScript", "React", "Node.js", "PostgreSQL", "Docker", "AWS"],
        "experience": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineering Intern",
                "duration": "June 2023 - Aug 2023",
                "description": "Developed a microservices-based architecture for real-time data processing.\nOptimized API response times by 40% using Redis caching."
            }
        ],
        "projects": [
            {
                "title": "AI Resume Parser",
                "technologies": ["Python", "FastAPI", "OpenAI"],
                "link": "https://github.com/johndoe/resume-parser",
                "description": "Built a tool that extracts structured data from PDF resumes using LLMs.\nImplemented a LaTeX generator for professional resume formatting."
            }
        ],
        "achievements": [
            "1st place in National Level Hackathon 2023",
            "Certified AWS Solutions Architect - Associate"
        ]
    }

    normalized = normalize_resume_json(sample_data)
    latex_code = generate_latex_resume(normalized)
    
    print("\nGenerated LaTeX Preview (First 20 lines):")
    print("-" * 40)
    print("\n".join(latex_code.splitlines()[:20]))
    print("-" * 40)
    
    assert "\\begin{document}" in latex_code
    assert "John Doe" in latex_code
    assert "VNR Vignana Jyothi" in latex_code
    print("LaTeX Generator Test Passed!\n")

async def test_backend_routes_logic():
    # This is a unit test for the service logic without needing a running server/DB if possible
    # But since it depends on DB models and LLM, we'll just check if imports and method signatures match.
    print("Verifying Backend Service Logic...")
    from agents.placements.resume_editor.services import ResumeEditorService
    service = ResumeEditorService()
    
    if hasattr(service, "improve_full_resume"):
        print("✓ improve_full_resume method found in ResumeEditorService")
    else:
        print("✗ improve_full_resume method NOT found")
        
    print("Verification Finished.")

if __name__ == "__main__":
    test_latex_generator()
    asyncio.run(test_backend_routes_logic())
