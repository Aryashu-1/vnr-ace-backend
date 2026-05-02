import asyncio
from agents.classwork.graphs import faculty_timetable_enquiry_graph
import json

async def test_faculty_enquiry():
    print("Testing Faculty Enquiry Agent...\n")
    
    # Mock user
    class MockUser:
        id = "550e8400-e29b-41d4-a716-446655440000"
        role = type('obj', (object,), {'name': 'student'})
    
    current_user = MockUser()
    
    # Test Case 1: Complex Query (Room lookup)
    # We'll see if the SQL generator handles "Where is Dr. S. Appa Rao on Saturday?"
    test_query = "What is the schedule for Ms. Sana Inayath on Monday?"
    
    initial_state = {
        "user_query": test_query,
        "user_role": "student",
        "user_id": current_user.id,
        "messages": [("human", test_query)],
        "audit_events": [],
        "memory": []
    }
    
    print(f"User Query: {test_query}")
    
    # Run the graph
    config = {"configurable": {"thread_id": "test_thread_1"}}
    result = await faculty_timetable_enquiry_graph.ainvoke(initial_state, config=config)
    
    print(f"\nIntent Detected: {result.get('intent')}")
    print(f"Data Strategy: {result.get('data_strategy')}")
    print(f"Rows Found: {len(result.get('query_result_rows', []))}")
    if result.get('query_result_rows'):
        print(f"Sample Row: {result.get('query_result_rows')[0]}")
    if result.get('sql_query'):
        print(f"SQL Generated: {result.get('sql_query')}")
    
    print(f"\nFinal Response:\n{result.get('final_response')}")
    print("-" * 50)

    # Test Case 2: Caching / Data Reuse
    # Ask a follow-up to see if it reuses data
    follow_up_query = "What is his designation?"
    print(f"\nFollow-up Query: {follow_up_query}")
    
    follow_up_state = result # Use the previous state
    follow_up_state["user_query"] = follow_up_query
    follow_up_state["messages"].append(("human", follow_up_query))
    
    result_2 = await faculty_timetable_enquiry_graph.ainvoke(follow_up_state, config=config)
    
    print(f"Data Strategy: {result_2.get('data_strategy')}")
    print(f"Final Response:\n{result_2.get('final_response')}")

if __name__ == "__main__":
    asyncio.run(test_faculty_enquiry())
