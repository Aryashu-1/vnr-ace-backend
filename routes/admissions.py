from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.guardrails import check_input_guardrail, check_output_guardrail
from ace_graphs.admissions_graph import admissions_graph


router = APIRouter(prefix="/admissions", tags=["Admissions"])


@router.post("/chat")
async def admissions_chat(
    body: dict,
    db: AsyncSession = Depends(get_db)
):
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    # Input Guardrail
    if not await check_input_guardrail(message):
        return {
            "reply": "I cannot process this request as it contains inappropriate or abusive language.",
            "route": "blocked_input"
        }

    # Prepare graph state
    initial_state = {
        "message": message,
        "reply": None,
        "route": None,
    }

    # Run graph
    result = await admissions_graph.ainvoke(initial_state)
    reply = result.get("reply")

    # Output Guardrail
    if reply and not await check_output_guardrail(reply, message):
        return {
            "reply": "I cannot provide a response to this request as it violates safety guidelines or contains sensitive information.",
            "route": "blocked_output"
        }

    return {
        "reply": reply,
        "route": result.get("route")   # optional debug info
    }
