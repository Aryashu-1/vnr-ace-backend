import asyncio
import sys
import os

# Add the parent directory to sys.path to import the agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.admissions.graph import admissions_graph
from agents.admissions.services import AdmissionsDataService

async def test_admissions_scenarios():
    # Initialize the cache since we're not running through the FastAPI lifespan
    await AdmissionsDataService.fetch_departments_from_db()
    
    test_cases = [
        {
            "name": "General Greeting",
            "message": "Hello, I am interested in joining VNR College.",
            "expected_route": ["direct_response", "faq"] # Supervisor might answer directly or route to FAQ
        },
        {
            "name": "Specific Department Query",
            "message": "What is the fee structure for Computer Science Engineering?",
            "expected_route": ["faq", "department_query"]
        },
        {
            "name": "Branch Comparison",
            "message": "Which is better, CSE or ECE?",
            "expected_route": ["faq"]
        },
        {
            "name": "Application Tracking",
            "message": "Can you check my application status?",
            "expected_route": ["application_tracking"]
        }
    ]

    config = {"configurable": {"thread_id": "test_thread_1"}}

    for case in test_cases:
        print(f"\n--- Testing: {case['name']} ---")
        print(f"Message: {case['message']}")
        
        initial_state = {
            "message": case["message"],
            "messages": [("human", case["message"])],
            "history": ""
        }
        
        try:
            result = await admissions_graph.ainvoke(initial_state, config=config)
            print(f"Final Route: {result.get('route') or result.get('dept_route')}")
            reply = result.get('reply', '')
            # Encode and decode to handle characters like Rupee symbol in Windows console
            print(f"Response: {reply[:200].encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)}...")
        except Exception as e:
            print(f"Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(test_admissions_scenarios())
