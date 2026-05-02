import asyncio
import sys
import os

# Add the parent directory to sys.path to import the agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.classwork.graphs import report_generation_graph

async def test_report_generation():
    print("\n--- Testing: Report Generation Agent ---")
    
    # Scenario 1: Admin user (should fail due to ALLOWED_ROLES bug)
    print("\nScenario 1: Admin User request")
    initial_state_admin = {
        "user_query": "Generate a list of CSE students with attendance below 75%",
        "user_role": "admin",
        "user_id": "test_user_1",
        "messages": [("human", "Generate a list of CSE students with attendance below 75%")],
        "audit_events": []
    }
    
    config = {"configurable": {"thread_id": "test_report_thread"}}
    
    try:
        result = await report_generation_graph.ainvoke(initial_state_admin, config=config)
        print(f"Final Response: {result.get('final_response')}")
        print(f"Access Granted: {result.get('access_granted')}")
    except Exception as e:
        print(f"Error: {e}")

    # Scenario 2: Faculty user (should pass access control)
    print("\nScenario 2: Faculty User request")
    initial_state_faculty = {
        "user_query": "Give me a list of all students in IT department",
        "user_role": "faculty",
        "user_id": "test_faculty_1",
        "messages": [("human", "Give me a list of all students in IT department")],
        "audit_events": []
    }
    
    try:
        # Note: This might fail later in load_data or planner if LLM is not configured 
        # or DB is empty, but we want to check access control first.
        result = await report_generation_graph.ainvoke(initial_state_faculty, config=config)
        print(f"Final Response: {result.get('final_response')}")
        print(f"Access Granted: {result.get('access_granted')}")
        print(f"Report Type: {result.get('report_type')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_report_generation())
