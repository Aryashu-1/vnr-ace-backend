import asyncio
import sys
import os

# Add the parent directory to sys.path to import the agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.placements.graphs import interview_prep_graph

async def test_interview_prep():
    print("\n--- Testing: Interview Prep Agent (DB-backed) ---")
    
    # Test case 1: Oracle DSA questions
    print("\nScenario 1: Oracle DSA questions")
    state_oracle = {
        "user_query": "binary search and linked list",
        "company": "Oracle",
        "topics": ["DSA"],
        "messages": [("human", "Tell me about Oracle DSA questions")],
        "audit_events": []
    }
    
    config = {"configurable": {"thread_id": "test_interview_oracle"}}
    result = await interview_prep_graph.ainvoke(state_oracle, config=config)
    
    print(f"Questions Found: {len(result.get('filtered_questions', []))}")
    if result.get('filtered_questions'):
        print(f"Sample Question: {result['filtered_questions'][0]['question']}")
    
    # print(f"\nResponse preview: {result['response'][:200]}...")

    # Test case 2: General fallback
    print("\nScenario 2: Fallback teaching")
    state_fallback = {
        "user_query": "how to explain my project",
        "company": "RandomCompany",
        "messages": [("human", "how to explain my project")],
        "audit_events": []
    }
    
    config = {"configurable": {"thread_id": "test_interview_fallback"}}
    result = await interview_prep_graph.ainvoke(state_fallback, config=config)
    print(f"Questions Found: {len(result.get('filtered_questions', []))}")
    # print(f"Response preview: {result['response'][:200]}...")

if __name__ == "__main__":
    asyncio.run(test_interview_prep())
