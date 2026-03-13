import asyncio
from ace_graphs.tp_admin_graph import tp_admin_agent
from app import lifespan, app

async def main():
    print("Testing T&P Admin Agent...")
    
    # Run the FastAPI lifespan to initialize DB engine
    async with lifespan(app):
        initial_state = {"messages": []}
        result = await tp_admin_agent.ainvoke(initial_state)
        
        print("\n=== Agent Result ===\n")
        for msg in result.get("messages", []):
            msg_type = type(msg).__name__
            print(f"[{msg_type}]: {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
