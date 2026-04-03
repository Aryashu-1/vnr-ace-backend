import asyncio
import json
from agents.placements.graphs import interview_prep_graph

async def test_graph():
    print("Testing Interview Prep Graph...")
    
    initial_state = {
        "company": "Oracle",
        "topics": ["DSA"],
        "user_query": "How to handle a situation where I don't know the answer in an interview?",
        "session_id": "test-session-fallback",
        "audit_events": []
    }
    
    try:
        # Run graph
        result = await interview_prep_graph.ainvoke(initial_state)
        
        print("\n--- Result ---")
        print(f"Company: {result.get('company')}")
        print(f"Filtered Questions Count: {len(result.get('filtered_questions', []))}")
        print("\nAI Response:")
        print(result.get('response'))
        print("\nAudit Events:")
        for event in result.get('audit_events', []):
            print(f"- {event.get('details', {}).get('action')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_graph())
