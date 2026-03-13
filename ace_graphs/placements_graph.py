from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from core.llm import call_llm

# ---------------------------
#   State Definition
# ---------------------------

class PlacementsState(TypedDict):
    user_id: Optional[int]
    role: Optional[str]  # e.g., 'student', 'admin', 'coordinator'
    message: str
    intent: Optional[str]
    authorized: bool
    response: Optional[str]
    validation_status: Optional[str] # 'approved', 'rejected'
    # Company Prep fields
    company_name: Optional[str]
    job_role: Optional[str]
    company_context: Optional[dict]
    search_results: Optional[list]
    questions: Optional[list]

# ---------------------------
#   GENERIC NODES (Reusable)
# ---------------------------

async def rbac_node(state: PlacementsState):
    """
    Checks authorization. 
    NOTE: Bypassed for testing as per request.
    """
    return {"authorized": True}

async def validator_node(state: PlacementsState):
    """
    Validates the generated response.
    """
    response = state.get("response")
    if response and "error" not in response.lower():
        return {"validation_status": "approved"}
    return {"validation_status": "rejected"}

# ---------------------------
#   DASHBOARD GRAPH
# ---------------------------

async def dashboard_agent(state: PlacementsState):
    # Simulated logic
    return {"response": "Here is your Placement Dashboard: \n- Eligible: 5 Companies\n- Applied: 2\n- Status: In Progress"}

dashboard_builder = StateGraph(PlacementsState)
dashboard_builder.add_node("rbac", rbac_node)
dashboard_builder.add_node("dashboard_agent", dashboard_agent)
dashboard_builder.add_node("validator", validator_node)

dashboard_builder.set_entry_point("rbac")
dashboard_builder.add_edge("rbac", "dashboard_agent")
dashboard_builder.add_edge("dashboard_agent", "validator")
dashboard_builder.add_edge("validator", END)

dashboard_graph = dashboard_builder.compile()

# ---------------------------
#   RESUME GRAPH
# ---------------------------

async def resume_agent(state: PlacementsState):
    prompt = f"Analyze this resume request: {state['message']}. Return a constructive critique. IMPORTANT: Your scope is strictly limited to Placements and Resumes. If the user asks anything outside of this scope, you MUST immediately respond exactly with: 'I cannot handle this request, out of boundary. Please ask something related to Placements.'"
    # response = await call_llm(prompt) 
    response = "Resume Analysis: formatting looks good, add more metrics to your projects." # Mock for speed
    return {"response": response}

resume_builder = StateGraph(PlacementsState)
resume_builder.add_node("rbac", rbac_node)
resume_builder.add_node("resume_agent", resume_agent)
resume_builder.add_node("validator", validator_node)

resume_builder.set_entry_point("rbac")
resume_builder.add_edge("rbac", "resume_agent")
resume_builder.add_edge("resume_agent", "validator")
resume_builder.add_edge("validator", END)

resume_graph = resume_builder.compile()

# ---------------------------
#   PREP GRAPH
# ---------------------------

import os
from pathlib import Path
import json

async def load_company_context(company_name: str) -> dict:
    """Load company-specific context files"""
    company_dir = Path(f"data/companies/{company_name.lower().replace(' ', '_')}")
    
    context = {
        "company_info": "",
        "tech_stack": "",
        "culture": "",
        "tips": ""
    }
    
    if company_dir.exists():
        for file in company_dir.glob("*.txt"):
            key = file.stem
            try:
                context[key] = file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Error reading {file}: {e}")
    
    return context

async def search_tavily_questions(company_name: str, role: str = "") -> list:
    """Search Tavily for recent interview questions"""
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key or api_key == "your_tavily_api_key_here":
            print("Tavily API key not configured, skipping web search")
            return []
        
        client = TavilyClient(api_key=api_key)
        
        query = f"{company_name} interview questions {role} 2024 2025 experience"
        
        results = client.search(
            query=query,
            search_depth="basic",
            max_results=5
        )
        
        questions_from_web = []
        for result in results.get("results", []):
            questions_from_web.append({
                "source": result.get("url", ""),
                "content": result.get("content", "")[:500]  # Limit content length
            })
        
        return questions_from_web
    except Exception as e:
        print(f"Tavily search error: {e}")
        return []

def format_search_results(search_results: list) -> str:
    """Format search results for LLM prompt"""
    if not search_results:
        return "No recent web search results available."
    
    formatted = ""
    for i, result in enumerate(search_results, 1):
        formatted += f"\nSource {i}: {result.get('source', 'Unknown')}\n"
        formatted += f"{result.get('content', '')}\n"
    
    return formatted

async def generate_questions_with_llm(
    company: str,
    context: dict,
    search_results: list,
    role: str = "Software Engineer"
) -> list:
    """Generate top 20 interview questions using LLM"""
    
    prompt = f"""Generate the top 20 most relevant and realistic interview questions for {company} - {role} position.

Company Context:
{context.get('company_info', 'General tech company')}

Tech Stack/Focus Areas:
{context.get('tech_stack', 'Not specified')}

Company Culture:
{context.get('culture', 'Not specified')}

Recent Interview Insights from Web:
{format_search_results(search_results)}

Generate exactly 20 questions categorized as follows:
1. Technical Questions (8-10 questions) - coding, system design, algorithms
2. Behavioral Questions (4-5 questions) - teamwork, conflict, leadership
3. Company-Specific Questions (3-4 questions) - products, culture, values
4. HR/General Questions (2-3 questions) - career goals, strengths/weaknesses

For each question, provide:
- Category (Technical/Behavioral/Company-Specific/HR)
- Question text
- Difficulty (Easy/Medium/Hard)
- Brief reason why this question is relevant (1 sentence)

Format as JSON array:
[
  {{
    "category": "Technical",
    "question": "Design a scalable...",
    "difficulty": "Hard",
    "relevance": "Tests system design skills..."
  }},
  ...
]

Return ONLY the JSON array, no additional text.
IMPORTANT: Your scope is strictly limited to interview preparation for placements. If the company or role is completely unrelated to tech companies or job placements, return exactly this JSON array: [{"category": "Error", "question": "I cannot handle this request, out of boundary. Please ask something related to interview preparation for placements.", "difficulty": "N/A", "relevance": "N/A"}]"""

    try:
        response = await call_llm(prompt)
        
        # Try to parse JSON from response
        # LLM might wrap in ```json or other markers
        response_clean = response.strip()
        if "```json" in response_clean:
            response_clean = response_clean.split("```json")[1].split("```")[0].strip()
        elif "```" in response_clean:
            response_clean = response_clean.split("```")[1].split("```")[0].strip()
        
        questions = json.loads(response_clean)
        
        # Ensure we have exactly 20 questions
        if len(questions) > 20:
            questions = questions[:20]
        
        return questions
    except Exception as e:
        print(f"Error generating questions: {e}")
        # Fallback to basic questions
        return generate_fallback_questions(company, role)

def generate_fallback_questions(company: str, role: str) -> list:
    """Generate basic fallback questions if LLM fails"""
    return [
        {"category": "Technical", "question": f"Describe your experience with the technologies used at {company}.", "difficulty": "Medium", "relevance": "Assesses technical background"},
        {"category": "Technical", "question": "Explain a complex technical problem you solved recently.", "difficulty": "Medium", "relevance": "Tests problem-solving skills"},
        {"category": "Behavioral", "question": "Tell me about a time you worked in a team.", "difficulty": "Easy", "relevance": "Evaluates teamwork"},
        {"category": "Behavioral", "question": "How do you handle tight deadlines?", "difficulty": "Medium", "relevance": "Tests stress management"},
        {"category": "Company-Specific", "question": f"Why do you want to work at {company}?", "difficulty": "Easy", "relevance": "Gauges motivation"},
        {"category": "HR", "question": "Where do you see yourself in 5 years?", "difficulty": "Easy", "relevance": "Assesses career goals"},
    ]

def format_questions_response(questions: list, company: str, role: str) -> str:
    """Format questions as markdown"""
    
    response = f"# Top {len(questions)} Interview Questions for {company} - {role}\n\n"
    
    categories = {
        "Technical": [],
        "Behavioral": [],
        "Company-Specific": [],
        "HR": []
    }
    
    # Group by category
    for q in questions:
        cat = q.get("category", "Technical")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(q)
    
    # Format each category
    for category, qs in categories.items():
        if qs:
            response += f"## {category} Questions ({len(qs)})\n\n"
            for i, q in enumerate(qs, 1):
                response += f"**Q{i}. {q.get('question', 'N/A')}**\n"
                response += f"- *Difficulty*: {q.get('difficulty', 'Medium')}\n"
                response += f"- *Why relevant*: {q.get('relevance', 'Standard interview question')}\n\n"
    
    return response

async def prep_agent(state: PlacementsState):
    """
    Generate top 20 company-specific interview questions.
    Uses company context + Tavily search + LLM generation.
    """
    message = state.get("message", "")
    
    # Extract company name and role from message or state
    company = state.get("company_name", "")
    role = state.get("job_role", "Software Engineer")
    
    # Try to extract from message if not in state
    if not company and message:
        # Simple extraction: assume format like "Google SDE" or "Amazon Software Engineer"
        parts = message.split()
        if len(parts) > 0:
            company = parts[0]
        if len(parts) > 1:
            role = " ".join(parts[1:])
    
    if not company:
        company = "General Tech Company"
    
    print(f"[Prep Agent] Generating questions for {company} - {role}")
    
    # 1. Load company context
    context = await load_company_context(company)
    print(f"[Prep Agent] Loaded context: {list(context.keys())}")
    
    # 2. Search Tavily for recent questions
    search_results = await search_tavily_questions(company, role)
    print(f"[Prep Agent] Found {len(search_results)} web search results")
    
    # 3. Generate questions with LLM
    questions = await generate_questions_with_llm(company, context, search_results, role)
    print(f"[Prep Agent] Generated {len(questions)} questions")
    
    # 4. Format response
    formatted_response = format_questions_response(questions, company, role)
    
    return {
        "response": formatted_response,
        "company_name": company,
        "job_role": role,
        "company_context": context,
        "search_results": search_results,
        "questions": questions
    }

prep_builder = StateGraph(PlacementsState)
prep_builder.add_node("rbac", rbac_node)
prep_builder.add_node("prep_agent", prep_agent)
prep_builder.add_node("validator", validator_node)

prep_builder.set_entry_point("rbac")
prep_builder.add_edge("rbac", "prep_agent")
prep_builder.add_edge("prep_agent", "validator")
prep_builder.add_edge("validator", END)

prep_graph = prep_builder.compile()

# ---------------------------
#   SHORTLISTING GRAPH
# ---------------------------

async def shortlisting_agent(state: PlacementsState):
    return {"response": "You have been shortlisted for: \n- TechCorp Inc.\n- Global Solutions"}

shortlisting_builder = StateGraph(PlacementsState)
shortlisting_builder.add_node("rbac", rbac_node)
shortlisting_builder.add_node("shortlisting_agent", shortlisting_agent)
shortlisting_builder.add_node("validator", validator_node)

shortlisting_builder.set_entry_point("rbac")
shortlisting_builder.add_edge("rbac", "shortlisting_agent")
shortlisting_builder.add_edge("shortlisting_agent", "validator")
shortlisting_builder.add_edge("validator", END)

shortlisting_graph = shortlisting_builder.compile()

# ---------------------------
#   TRACKING GRAPH
# ---------------------------

async def tracking_agent(state: PlacementsState):
    return {"response": "Tracking Update: Your application to Cloud Systems is 'Under Review'."}

tracking_builder = StateGraph(PlacementsState)
tracking_builder.add_node("rbac", rbac_node)
tracking_builder.add_node("tracking_agent", tracking_agent)
tracking_builder.add_node("validator", validator_node)

tracking_builder.set_entry_point("rbac")
tracking_builder.add_edge("rbac", "tracking_agent")
tracking_builder.add_edge("tracking_agent", "validator")
tracking_builder.add_edge("validator", END)

tracking_graph = tracking_builder.compile()

# ---------------------------
#   NOTIFICATION GRAPH
# ---------------------------

async def notification_agent(state: PlacementsState):
    return {"response": "No new notifications at this time."}

notification_builder = StateGraph(PlacementsState)
notification_builder.add_node("rbac", rbac_node)
notification_builder.add_node("notification_agent", notification_agent)
notification_builder.add_node("validator", validator_node)

notification_builder.set_entry_point("rbac")
notification_builder.add_edge("rbac", "notification_agent")
notification_builder.add_edge("notification_agent", "validator")
notification_builder.add_edge("validator", END)

notification_graph = notification_builder.compile()
