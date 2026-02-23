import sys
import importlib.util

def check_import(module_name):
    if importlib.util.find_spec(module_name) is None:
        print(f"[MISSING] {module_name} is NOT installed.")
        return False
    else:
        print(f"[OK] {module_name} is installed.")
        return True

def main():
    print("Verifying skill installations...")
    
    # Check open-interpreter
    interpreter_ok = check_import("interpreter")
    
    # Check gpt-researcher
    researcher_ok = check_import("gpt_researcher")
    
    # Check browser-use
    browser_ok = check_import("browser_use")
    
    # Check playwright
    playwright_ok = check_import("playwright")
    
    if all([interpreter_ok, researcher_ok, browser_ok]):
        print("\nAll main packages are installed.")
        
        # Check playwright browsers
        if playwright_ok:
            print("Checking playwright browsers...")
            print("Tip: If browser automation fails, run 'playwright install' manually.")
            
    else:
        print("\nSome packages are missing. Installation might have failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
