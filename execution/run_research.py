import asyncio
import sys
import os
from gpt_researcher import GPTResearcher

async def main():
    if len(sys.argv) < 2:
        print("Usage: python execution/run_research.py \"<query>\"")
        sys.exit(1)

    query = sys.argv[1]
    report_type = "research_report"

    # Initialize researcher
    researcher = GPTResearcher(query=query, report_type=report_type)
    
    # Conduct research
    print(f"Starting research on: {query}")
    await researcher.conduct_research()
    
    # Write report
    report = await researcher.write_report()
    
    # Save report
    output_path = os.path.join(".tmp", "research_report.md")
    os.makedirs(".tmp", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"Research complete. Report saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
