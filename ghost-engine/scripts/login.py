import time
from playwright.sync_api import sync_playwright

def run(supabase, device_id, job_id, payload):
    email = payload.get("email")
    password = payload.get("password")
    
    if not email or not password:
        raise ValueError("Missing email or password in payload")

    with sync_playwright() as p:
        # Launch browser with persistent context to save cookies
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./linkedin_session",
            headless=False, # We usually want Ghost laptops headed so we can debug, or False specifically for logging in
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.new_page()

        try:
            print("Navigating to LinkedIn login...")
            page.goto("https://www.linkedin.com/login", wait_until="networkidle")

            # Check if already logged in
            if "feed" in page.url:
                print("Already logged in.")
                return {"status": "success", "message": "Already logged in"}

            # Fill credentials
            page.fill("input#username", email)
            page.fill("input#password", password)
            page.click("button[type='submit']")

            print("Credentials submitted. Waiting for page load...")
            page.wait_for_load_state("networkidle")

            # Check for 2FA or Challenge
            if "checkpoint/challenge" in page.url or page.locator("input[name='pin']").is_visible() or page.locator("input#input__email_verification_pin").is_visible():
                print("2FA CHALLENGE DETECTED. Notifying Web UI...")
                
                # Update job status to trigger the Web UI 2FA Modal
                supabase.table("job_runs").update({
                    "status": "waiting_for_2fa"
                }).eq("id", job_id).execute()

                # Poll for code from the Web UI
                two_factor_code = None
                poll_interval = 3
                timeout = 300 # Wait up to 5 minutes for the user to submit the code
                waited = 0

                while waited < timeout:
                    print(f"Waiting for 2FA code... ({waited}/{timeout}s)")
                    
                    response = supabase.table("job_runs").select("payload, status").eq("id", job_id).execute()
                    if response.data and len(response.data) > 0:
                        current_status = response.data[0].get("status")
                        current_payload = response.data[0].get("payload", {})
                        
                        code = current_payload.get("two_factor_code")
                        if code and current_status != "waiting_for_2fa":
                            two_factor_code = code
                            print(f"Received 2FA code: {two_factor_code}")
                            break
                            
                    time.sleep(poll_interval)
                    waited += poll_interval

                if not two_factor_code:
                    raise Exception("Timed out waiting for 2FA code from the Web UI.")

                # Input the 2FA code
                pin_input = page.locator("input[name='pin'], input#input__email_verification_pin")
                if pin_input.is_visible():
                    pin_input.fill(two_factor_code)
                    
                    submit_btn = page.locator("button#email-pin-submit-button, button[type='submit']")
                    if submit_btn.is_visible():
                        submit_btn.click()
                        page.wait_for_load_state("networkidle")
                    else:
                        raise Exception("Could not find 2FA submit button")
                else:
                    raise Exception("2FA PIN input vanished")

            # Final verification
            if "feed" in page.url or "dashboard" in page.url:
                print("Login successful.")
                return {"status": "success", "message": "Logged in successfully"}
            else:
                raise Exception(f"Login failed or unexpected redirect. Current URL: {page.url}")

        finally:
            browser.close()
