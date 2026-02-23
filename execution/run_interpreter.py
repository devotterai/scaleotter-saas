import sys
import os
from interpreter import interpreter

def main():
    if len(sys.argv) < 2:
        print("Usage: python execution/run_interpreter.py \"<prompt>\"")
        sys.exit(1)

    prompt = sys.argv[1]
    
    # Configure interpreter
    interpreter.auto_run = True  # Enable auto-run for autonomous tasks
    interpreter.llm.model = "gpt-4o"  # Use GPT-4o for best results
    
    # Run the interpreter
    print(f"Running Open Interpreter with prompt: {prompt}")
    interpreter.chat(prompt)

if __name__ == "__main__":
    main()
