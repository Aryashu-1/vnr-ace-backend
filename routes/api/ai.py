from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from core.db import engine
from sqlalchemy import text
from core.llm import get_llm

router = APIRouter(prefix="/ai", tags=["AI Engine API"])

class AIQueryRequest(BaseModel):
    prompt: str

# System instructions to restrict what SQL can be generated
SQL_PROMPT = """
You are an expert PostgreSQL database assistant querying a placement database.
Given an input question, create a syntactically correct PostgreSQL query to run.
Return ONLY the raw SQL query. No explanations. No backticks or markdown formatting.

Here is the schema:
Table: students (id, roll_no, full_name, gender, dob, branch, email, mobile, cgpa, tenth_cgpa, inter_percent, active_backlogs, passive_backlogs, category, home_town, district, state, pincode, minor_degree, intern_status, created_at)
Table: companies (id, name, sector, created_at)
Table: placements (id, student_id, company_id, ctc_lpa, placement_date, is_internship, created_at)
Table: offers (id, student_id, company_id, ctc_lpa, offer_number, created_at)
Table: minor_degrees (id, student_id, minor_name)

Safety checks:
- You must NEVER execute INSERT, UPDATE, DELETE, DROP, ALTER or TRUNCATE statements.
- Query should be mapped appropriately to the schema above.

User Question: {question}
"""

@router.post("/query")
async def generate_sql_query(request: AIQueryRequest):
    try:
        llm = get_llm(temperature=0)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    prompt_template = PromptTemplate(template=SQL_PROMPT, input_variables=["question"])
    
    chain = prompt_template | llm
    
    try:
        # Step 1: Send prompt -> LLM -> Convert to SQL
        sql_response = await chain.ainvoke({"question": request.prompt})
        raw_sql = sql_response.content.strip().replace('```sql', '').replace('```', '')
        
        # Step 2: Validate safety
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]
        upper_sql = raw_sql.upper()
        if any(keyword in upper_sql for keyword in dangerous_keywords):
            return {"error": "Write operations are strictly prohibited for safety."}
            
        # Step 3: Execute query
        async with engine.connect() as conn:
            # Requires read-only transactions if supported, for extra safety
            cursor_result = await conn.execute(text(raw_sql))
            rows = cursor_result.all()
            
            # Format row objects into dictionaries using column keys
            results = [dict(zip(cursor_result.keys(), row)) for row in rows]
            
            # Decide chart type arbitrarily based on query nature
            chart_type = "table"
            if "count" in upper_sql or "groupby" in upper_sql.replace(" ", ""):
                chart_type = "bar" if len(results) < 10 else "line"

            return {
                "sql": raw_sql,
                "result": results,
                "chartType": chart_type
            }
            
    except Exception as e:
        return {"error": str(e), "sql": raw_sql if 'raw_sql' in locals() else None}
