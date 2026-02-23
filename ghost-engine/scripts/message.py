import time
import os
import random
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def random_sleep(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def update_status(supabase, cid, status):
    """Update candidate status in Supabase."""
    try:
        supabase.table("candidates").update({
            "campaign_status": status,
            "message_status": status if status == "replied" else "sent",
            "updated_at": "now()"
        }).eq("id", cid).execute()
        log(f"Candidate {cid} status updated to {status}")
    except Exception as e:
        log(f"Failed to update status for {cid}: {e}")

def human_scroll(page):
    try:
        for _ in range(random.randint(2, 5)):
            page.mouse.wheel(0, random.randint(300, 700))
            random_sleep(0.5, 1.5)
    except: pass

def run(supabase, device_id, job_id, campaign_id):
    log(f"STARTING MESSAGE AUTOMATION for campaign: {campaign_id}")
    
    # Fetch accepted candidates who haven't been messaged yet
    try:
        response = supabase.table("candidates").select("*") \
            .eq("campaign_id", campaign_id) \
            .eq("campaign_status", "accepted").execute()
            # Or campaign_status='message_pending' depending on architecture.
        candidates = response.data
    except Exception as e:
        raise Exception(f"Failed to fetch candidates: {e}")

    if not candidates:
        log("No accepted candidates found ready for messaging.")
        return {"status": "success", "message": "No candidates to process"}

    log(f"Found {len(candidates)} candidates to message.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./linkedin_session",
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--window-size=1280,800'
                ]
            )
            page = browser.new_page()
            
            page.goto("https://www.linkedin.com/feed/", timeout=30000, wait_until="domcontentloaded")
            random_sleep(2, 3)
            if "login" in page.url.lower():
                browser.close()
                raise Exception("Session expired. Please run the login job again.")

            for i, cand in enumerate(candidates):
                url = cand.get("linkedin_url")
                cid = cand.get("id")
                msg_text = cand.get("initial_message")
                
                if not msg_text:
                    log(f"Skipping {url}: No initial_message found.")
                    continue
                 
                log(f"[{i+1}/{len(candidates)}] Processing {url}...")
                
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                except: continue 

                human_scroll(page)
                random_sleep(1, 3)

                # Find Message Button
                message_btn = None
                for sel in ["button:has-text('Message')", "a.message-anywhere-button", "button[aria-label^='Message']"]:
                    message_btn = page.query_selector(sel)
                    if message_btn: break
                
                if message_btn:
                    log("Clicking Message button.")
                    page.evaluate("el => el.click()", message_btn)
                    random_sleep(1, 2)
                    
                    # Ensure modal opened
                    msg_box = page.locator(".msg-form__contenteditable, p").last
                    if msg_box.is_visible(timeout=3000):
                        log("Typing message...")
                        msg_box.fill("")
                        for char in msg_text:
                            msg_box.type(char, delay=random.randint(10, 30))
                            
                        random_sleep(1, 2)
                        
                        send_btn = page.locator("button[type='submit']").last
                        if send_btn.is_enabled():
                            send_btn.click()
                            log("SUCCESS: Message sent.")
                            update_status(supabase, cid, "message_sent")
                        else:
                            log("Send button not enabled.")
                    else:
                        log("Message composing box not found.")

                else:
                    log("Message button not found on profile.")
                    
                random_sleep(3, 7)

            browser.close()
            log("MESSAGING COMPLETE.")
            return {"status": "success", "processed": len(candidates)}

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        raise
