import sys
import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent

async def main():
    if len(sys.argv) < 2:
        print("Usage: python execution/browser_automation.py \"<task>\"")
        sys.exit(1)

    task = sys.argv[1]
    
    # Initialize the agent
    agent = Agent(
        task=task,
        llm=ChatOpenAI(model="gpt-4o"),
    )
    
    # Run the agent
    print(f"Starting browser automation task: {task}")
    result = await agent.run()
    
    print("Task execution complete.")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
