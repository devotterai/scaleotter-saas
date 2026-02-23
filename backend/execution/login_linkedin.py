
import argparse
import time
import sys
import os
from playwright.sync_api import sync_playwright

def login_linkedin(email, password):
    with sync_playwright() as p:
        # Launch browser in visible mode ("The Laptop" strategy)
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled'] # Simple stealth
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        print(f"Navigating to LinkedIn login for {email}...")
        page.goto("https://www.linkedin.com/login")
        
        # Simulate human-like typing
        print("Entering credentials...")
        page.fill("#username", email)
        time.sleep(0.5)
        page.fill("#password", password)
        time.sleep(0.5)
        
        print("Clicking Sign in...")
        page.click("button[type='submit']")
        
        # Wait for navigation - explicitly wait for feed or challenge
        # Increased timeout to 120s to allow for manual 2FA/Captcha
        try:
            print("Waiting for login success (feed load)... You have 2 minutes to solve any captcha.")
            page.wait_for_url("**/feed/**", timeout=120000) 
            print("Login successful! Feed loaded.")
            
            # Save state (cookies/storage)
            # Determine path relative to this script to be safe
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Save in the parent directory of 'execution' which is 'backend'
            backend_dir = os.path.dirname(script_dir)
            state_path = os.path.join(backend_dir, "state.json")
            
            context.storage_state(path=state_path)
            print(f"Session state saved to {state_path}")
            
        except Exception as e:
            print("Did not reach feed immediately. Might be a challenge or error.")
            print(f"Current URL: {page.url}")
            # If it's a challenge, we might want to keep it open or wait longer
            if "challenge" in page.url:
                print("Hit a challenge/2FA. Please solve it manually in the browser window if open.")
                # Wait another 60s
                time.sleep(60) 
                # Try saving state again after manual solve
                script_dir = os.path.dirname(os.path.abspath(__file__))
                backend_dir = os.path.dirname(script_dir)
                state_path = os.path.join(backend_dir, "state.json")
                context.storage_state(path=state_path)
                print(f"Saved state after wait period to {state_path}")
            else:
                # Re-raise if it's not a challenge or if we failed after waiting
                raise e

        # Keep browser open briefly to show the user it worked
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    
    login_linkedin(args.email, args.password)
