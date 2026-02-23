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
            "updated_at": "now()"
        }).eq("id", cid).execute()
        log(f"Candidate {cid} status updated to {status}")
    except Exception as e:
        log(f"Failed to update status for {cid}: {e}")

def check_daily_limit(supabase, limit=30):
    """Check if we've exceeded the daily connection limit across the org/device."""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = supabase.table("candidates").select("id", count="exact") \
            .eq("campaign_status", "connection_sent") \
            .gte("updated_at", f"{today}T00:00:00Z").execute()
        count = response.count if response.count else 0
        return count >= limit, count
    except Exception as e:
        log(f"Could not check daily limit: {e}")
        return False, 0

def human_scroll(page):
    try:
        for _ in range(random.randint(3, 7)):
            page.mouse.wheel(0, random.randint(300, 700))
            random_sleep(0.5, 1.5)
        if random.random() > 0.7:
             page.mouse.wheel(0, -300)
    except: pass

def run(supabase, device_id, job_id, campaign_id, org_id):
    log(f"STARTING CONNECT AUTOMATION for campaign: {campaign_id}")
    
    # 1. Fetch pending candidates
    try:
        response = supabase.table("candidates").select("*") \
            .eq("campaign_id", campaign_id) \
            .eq("campaign_status", "pending").execute()
        candidates = response.data
    except Exception as e:
        raise Exception(f"Failed to fetch candidates: {e}")

    if not candidates:
        log("No pending candidates found in this campaign.")
        return {"status": "success", "message": "No candidates to process"}

    log(f"Found {len(candidates)} pending candidates.")

    # Selectors dictionary
    sel = {
        "connect_btn_primary": "button:has-text('Connect'):visible",
        "connect_btn_aria": "button[aria-label='Connect']:visible",
        "pending_text": "Pending",
        "message_text": "Message",
        "more_btn_selectors": [
            ".pv-top-card button:has(svg[id='overflow-web-ios-small'])",
            ".pv-top-card button[aria-label='More']",
            ".pv-top-card button[aria-label='More actions']",
            "button:has(svg[id='overflow-web-ios-small'])"
        ],
        "dropdown_connect_text": "Connect",
        "dropdown_connect_span": "span:has-text('Connect')",
        "send_without_note_aria": "button[aria-label='Send without a note']",
        "add_note_btn": "button[aria-label='Add a note']",
        "note_textarea": "textarea[name='message']",
        "send_btn": "button[aria-label='Send invitation']",
        "email_input": "input[name='email']",
        "dismiss_modal": "button[aria-label='Dismiss']"
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./linkedin_session",
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--window-size=1280,800'
                ]
            )
            page = browser.new_page()
            
            # Health check
            page.goto("https://www.linkedin.com/feed/", timeout=30000, wait_until="domcontentloaded")
            random_sleep(2, 3)
            if "login" in page.url.lower():
                browser.close()
                raise Exception("Session expired. Please run the login job again.")

            daily_limit = 30
            is_limit_reached, count = check_daily_limit(supabase, daily_limit)
            if is_limit_reached:
                log(f"DAILY LIMIT REACHED ({count}/{daily_limit}). Stopping.")
                browser.close()
                return {"status": "success", "message": "Daily limit reached"}

            for i, cand in enumerate(candidates):
                url = cand.get("linkedin_url")
                cid = cand.get("id")
                note = cand.get("connection_note")
                
                # Check limit
                is_limit_reached, count = check_daily_limit(supabase, daily_limit)
                if is_limit_reached:
                    log("Daily limit reached during execution.")
                    break
                 
                log(f"[{i+1}/{len(candidates)}] Processing {url}...")
                
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                except Exception as e:
                    log(f"Navigation failed: {e}")
                    continue 

                human_scroll(page)
                random_sleep(2, 4)

                # Check if Pending
                if page.locator("button", has_text=sel["pending_text"]).first.is_visible(timeout=2000):
                    log(f"Skipping: Connection already pending.")
                    update_status(supabase, cid, "connection_sent") 
                    continue

                # Check if Connected
                has_message_btn = page.locator("button", has_text=sel["message_text"]).first.is_visible(timeout=2000)

                # Find Connect
                connect_btn = page.query_selector(sel["connect_btn_primary"]) or page.query_selector(sel["connect_btn_aria"])
                success = False

                if not connect_btn:
                    log("Connect button not found in primary. Checking 'More'...")
                    more_btn = None
                    for ms in sel["more_btn_selectors"]:
                        try:
                            btn = page.query_selector(f"{ms}:visible")
                            if btn:
                                more_btn = btn
                                break
                        except: pass
                            
                    if more_btn:
                        more_btn.scroll_into_view_if_needed()
                        page.evaluate("el => el.click()", more_btn)
                        random_sleep(1, 2)
                            
                        connect_in_dropdown = page.get_by_text(sel["dropdown_connect_text"], exact=True).first
                        if not connect_in_dropdown.is_visible():
                            connect_in_dropdown = page.locator(sel["dropdown_connect_span"]).first
                        
                        if connect_in_dropdown.is_visible():
                            page.evaluate("el => el.click()", connect_in_dropdown)
                            success = True 
                        else:
                            log("Connect option not found in dropdown.")
                            if has_message_btn:
                                update_status(supabase, cid, "connection_sent")
                            continue
                    else:
                        log("'More' button not found.")
                        if has_message_btn:
                            update_status(supabase, cid, "connection_sent")
                        continue
                else:
                    page.evaluate("el => el.click()", connect_btn)
                    success = True

                random_sleep(1, 3)

                if success:
                    # Check "How do you know" modal
                    try:
                        if page.get_by_text("How do you know", exact=False).is_visible(timeout=2000):
                            other_btn = page.locator("button", has_text="Other")
                            if other_btn.is_visible():
                                other_btn.click()
                                random_sleep(0.5, 1)
                                page.locator("button", has_text="Connect").click()
                            else:
                                continue 
                    except: pass
                    
                    # Wait for modal
                    random_sleep(1.5, 3)
                    modal_handled = False

                    if note:
                        try:
                            add_note_btn = page.locator(sel["add_note_btn"]).first
                            if add_note_btn.is_visible(timeout=2000):
                                add_note_btn.click()
                                random_sleep(0.5, 1)
                                
                                textarea = page.locator(sel["note_textarea"]).first
                                if textarea.is_visible(timeout=2000):
                                    textarea.fill("")
                                    for char in note[:300]: # max characters allowed
                                        textarea.type(char, delay=random.randint(10, 50))
                                    random_sleep(0.5, 1)
                                    
                                    send_btn = page.locator(sel["send_btn"]).first
                                    if send_btn.is_visible(timeout=2000):
                                        send_btn.click()
                                        log(f"SUCCESS: Connection sent with note")
                                        update_status(supabase, cid, "connection_sent")
                                        modal_handled = True
                        except Exception as e:
                            log(f"Error during note flow: {e}.")

                    if not modal_handled:
                        # Try to send without note
                        send_now_btn = None
                        for sw_sel in [sel["send_without_note_aria"], "button[aria-label='Send now']"]:
                            try:
                                sb = page.locator(sw_sel).first
                                if sb.is_visible(timeout=2000):
                                    send_now_btn = sb
                                    break
                            except: pass
                        
                        if send_now_btn:
                            send_now_btn.click()
                            log(f"SUCCESS: Connection sent without note")
                            update_status(supabase, cid, "connection_sent")
                            modal_handled = True

                    if not modal_handled:
                        # Fallback verify
                        if page.locator("button", has_text="Pending").first.is_visible(timeout=2000):
                            log(f"SUCCESS: Connection sent directly")
                            update_status(supabase, cid, "connection_sent")
                        else:
                            log("Failed to verify connection was sent.")

                # Keep heartbeat alive
                random_sleep(3, 7)

            browser.close()
            log("AUTOMATION COMPLETE.")
            return {"status": "success", "processed": len(candidates)}

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        raise
