import argparse
import time
import os
import sys
import json
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

# Add backend dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import update_campaign_status, init_db
from account_health import get_dynamic_daily_limit

# Ensure tables exist (this script runs as a subprocess, outside FastAPI)
init_db()

import sqlite3

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
LOG_PATH = os.path.join(BACKEND_DIR, "automation.log")
DB_PATH = os.path.join(BACKEND_DIR, "candidates.db")
SELECTORS_PATH = os.path.join(SCRIPT_DIR, "selectors.json")
STATE_PATH = os.path.join(BACKEND_DIR, "state.json")

def log(msg):
    """Log to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except: pass

def load_selectors():
    """Load CSS selectors from JSON for hot-fix capability."""
    defaults = {
        "connect_btn_primary": "button:has-text('Connect'):visible",
        "connect_btn_aria": "button[aria-label='Connect']:visible",
        "pending_text": "Pending",
        "message_text": "Message",
        "more_btn_selectors": [
            ".pv-top-card button:has(svg[id='overflow-web-ios-small'])",
            ".pv-top-card button[aria-label='More']",
            ".pv-top-card button[aria-label='More actions']",
            ".pv-top-card-v2-ctas button[aria-label='More']",
            "button:has(svg[id='overflow-web-ios-small'])"
        ],
        "dropdown_connect_text": "Connect",
        "dropdown_connect_span": "span:has-text('Connect')",
        "send_without_note_aria": "button[aria-label='Send without a note']",
        "send_without_note_content": "Send without a note",
        "add_note_btn": "button[aria-label='Add a note']",
        "note_textarea": "textarea[name='message']",
        "send_btn": "button[aria-label='Send invitation']",
        "email_input": "input[name='email']",
        "dismiss_modal": "button[aria-label='Dismiss']"
    }
    try:
        if os.path.exists(SELECTORS_PATH):
            with open(SELECTORS_PATH, "r") as f:
                loaded = json.load(f)
                defaults.update(loaded)
                log(f"Loaded {len(loaded)} selectors from selectors.json")
    except Exception as e:
        log(f"Warning: Could not load selectors.json: {e}")
    return defaults

def random_sleep(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def check_daily_limit(limit=30):
    """Check if we've exceeded the daily connection limit."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT count(*) FROM campaign_candidates WHERE status='connection_sent' AND updated_at LIKE ?", (f"{today}%",))
        count = c.fetchone()[0]
        conn.close()
        return count >= limit, count
    except Exception as e:
        log(f"Warning: Could not check daily limit: {e}")
        return False, 0

def human_scroll(page):
    """Scrolls the page like a human reading."""
    try:
        for _ in range(random.randint(3, 7)):
            scroll_amount = random.randint(300, 700)
            page.mouse.wheel(0, scroll_amount)
            random_sleep(0.5, 1.5)
        if random.random() > 0.7:
             page.mouse.wheel(0, -300)
    except: pass

def take_failure_screenshot(page, name_prefix):
    """Saves a screenshot for debugging."""
    try:
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = f"debug_{name_prefix}_{timestamp}.png"
        path = os.path.join(BACKEND_DIR, "logs", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        page.screenshot(path=path)
        log(f"Screenshot saved to {path}")
    except: pass

def check_business_hours(start_hour=9, end_hour=18):
    """Returns True if within working hours."""
    now = datetime.now()
    if now.weekday() >= 5:
        log("Weekend detected. Skipping automation.")
        return False
    if start_hour <= now.hour < end_hour:
        return True
    log(f"Outside business hours ({start_hour}-{end_hour}). Current hour: {now.hour}")
    return False

def check_blacklist(candidate_id):
    """Checks if candidate is in the global exclusion list."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM campaign_candidates WHERE candidate_id = ? AND status IN ('connection_sent', 'accepted', 'replied')", (candidate_id,))
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except: return False

def perform_passive_engagement(page):
    """Scroll the LinkedIn feed and randomly like posts (stealth behavior)."""
    try:
        log("Performing passive engagement (feed scroll + random likes)...")
        page.goto("https://www.linkedin.com/feed/", timeout=30000, wait_until="domcontentloaded")
        random_sleep(2, 4)
        
        for _ in range(random.randint(5, 12)):
            page.mouse.wheel(0, random.randint(400, 800))
            random_sleep(1, 3)
            
            # 10% chance to like a post
            if random.random() < 0.10:
                try:
                    like_btns = page.locator("button[aria-label*='Like']").all()
                    if like_btns:
                        btn = random.choice(like_btns[:5])
                        if btn.is_visible():
                            btn.click()
                            log("Liked a post (passive engagement)")
                            random_sleep(1, 2)
                except: pass
        
        log("Passive engagement complete.")
    except Exception as e:
        log(f"Passive engagement error (non-fatal): {e}")

def random_idle():
    """Simulate a human taking a break — 30-60 second pause."""
    if random.random() < 0.15:  # 15% chance per candidate
        idle_time = random.randint(30, 60)
        log(f"Taking a random idle break for {idle_time}s (human simulation)...")
        time.sleep(idle_time)

def session_health_check(page):
    """Verify we're still logged in by checking the feed."""
    try:
        page.goto("https://www.linkedin.com/feed/", timeout=30000, wait_until="domcontentloaded")
        random_sleep(2, 3)
        
        # Check for login redirect
        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            log("CRITICAL: Session expired or account locked. Stopping.")
            return False
        
        log("Session health check passed.")
        return True
    except Exception as e:
        log(f"Session health check failed: {e}")
        return False


def connect_to_profiles(candidates, campaign_id):
    """Main automation loop."""
    log(f"STARTING AUTOMATION for {len(candidates)} candidates")
    
    # Load remote selectors
    sel = load_selectors()
    
    if not os.path.exists(STATE_PATH):
        log("ERROR: No login state found. Please login first.")
        return

    try:
        with sync_playwright() as p:
            # Stealth browser launch (Level 3)
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--window-position=0,0',
                    '--ignore-certificate-errors',
                    '--window-size=1280,800'
                ]
            )
            context = browser.new_context(
                storage_state=STATE_PATH,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Mask webdriver property (Level 3)
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            # Session Health Check (Level 3)
            if not session_health_check(page):
                browser.close()
                return
            
            # Passive Engagement before starting (Level 5)
            perform_passive_engagement(page)

            # Dynamic Daily Limit from Warm-up Ramp (Level 5)
            dynamic_limit = get_dynamic_daily_limit()
            is_limit_reached, count = check_daily_limit(dynamic_limit)
            if is_limit_reached:
                log(f"DAILY LIMIT REACHED ({count}/{dynamic_limit}). Stopping automation for safety.")
                browser.close()
                return
            
            log(f"Dynamic daily limit: {dynamic_limit} (sent today: {count})")

            # Business Hours Check (Level 4) -- Uncomment for production
            # if not check_business_hours():
            #     browser.close()
            #     return

            for i, cand in enumerate(candidates):
                url = cand.get("url")
                cid = cand.get("id")
                note = cand.get("note")  # AI-generated note (may be None)
                
                # Random Idle (Level 5) — simulate human distractions
                random_idle()
                
                # Global Blacklist Check (Level 4)
                if check_blacklist(cid):
                    log(f"Skipping {url}: Candidate in Global Blacklist (already contacted).")
                    update_campaign_status(campaign_id, cid, "skipped_blacklisted")
                    continue

                # Re-check limit periodically
                is_limit_reached, count = check_daily_limit(dynamic_limit)
                if is_limit_reached:
                    log(f"DAILY LIMIT REACHED ({count}/{dynamic_limit}). Stopping.")
                    break
                 
                log(f"[{i+1}/{len(candidates)}] Processing {url}...")
                
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                except Exception as e:
                    log(f"Navigation failed: {e}")
                    take_failure_screenshot(page, "nav_error")
                    continue 

                # Human Scroll (Level 3)
                human_scroll(page)
                random_sleep(2, 4)

                # --- 1. Check for PENDING state ---
                is_pending = False
                try:
                    if page.locator("button", has_text=sel["pending_text"]).first.is_visible(timeout=2000):
                        is_pending = True
                except: pass
                
                if is_pending:
                    log(f"Skipping {url}: Connection already pending.")
                    update_campaign_status(campaign_id, cid, "connection_sent") 
                    continue

                # --- 2. Check for CONNECTED state ---
                has_message_btn = False
                try:
                    has_message_btn = page.locator("button", has_text=sel["message_text"]).first.is_visible(timeout=2000)
                except: pass

                # --- 3. Try finding "Connect" button ---
                connect_btn = page.query_selector(sel["connect_btn_primary"])
                if not connect_btn:
                    connect_btn = page.query_selector(sel["connect_btn_aria"])
                
                success = False

                if not connect_btn:
                    log("Connect button not found in primary actions. Checking 'More' menu...")
                    
                    more_btn = None
                    for ms in sel["more_btn_selectors"]:
                        try:
                            btn = page.query_selector(f"{ms}:visible")
                            if btn:
                                more_btn = btn
                                log(f"Found More button with selector: {ms}")
                                break
                        except: continue
                            
                    if more_btn:
                        log("Clicking 'More' button...")
                        try:
                            page.evaluate("el => el.click()", more_btn)
                        except: pass
                        
                        menu_opened = False
                        for _ in range(3):
                            random_sleep(1, 2)
                            connect_in_dropdown = page.locator(f"text={sel['dropdown_connect_text']}").first
                            if connect_in_dropdown.is_visible():
                                menu_opened = True
                                break
                            
                        if not menu_opened:
                            log("Menu didn't open. Retrying with standard click...")
                            try:
                                more_btn.click()
                            except: pass
                            random_sleep(1, 2)
                            
                        connect_in_dropdown = page.get_by_text(sel["dropdown_connect_text"], exact=True).first
                        if not connect_in_dropdown.is_visible():
                            connect_in_dropdown = page.locator(sel["dropdown_connect_span"]).first
                        
                        if connect_in_dropdown.is_visible():
                            log("Found Connect in dropdown. Clicking...")
                            try:
                                connect_in_dropdown.click()
                            except:
                                page.evaluate("el => el.click()", connect_in_dropdown)
                            connect_btn = None 
                            success = True 
                        else:
                            log(f"Skipping {url}: Connect option not found in dropdown.")
                            if has_message_btn:
                                log(f"Assuming already connected (Message button present).")
                                update_campaign_status(campaign_id, cid, "connection_sent")
                            continue
                    else:
                        log(f"Skipping {url}: 'More' button not found.")
                        if has_message_btn:
                            log(f"Assuming already connected (Message button present).")
                            update_campaign_status(campaign_id, cid, "connection_sent")
                        continue
                else:
                    log(f"Found primary Connect button. Clicking...")
                    page.evaluate("el => el.click()", connect_btn)
                    success = True

                random_sleep(1, 3)

                if success:
                    # Hardening: Check for "How do you know" modal
                    try:
                        if page.get_by_text("How do you know", exact=False).is_visible(timeout=2000):
                            log("Detected 'How do you know' modal.")
                            other_btn = page.locator("button", has_text="Other")
                            if other_btn.is_visible():
                                other_btn.click()
                                random_sleep(0.5, 1)
                                page.locator("button", has_text="Connect").click()
                            else:
                                log("Unknown contact relation options. Cancelling for safety.")
                                take_failure_screenshot(page, "unknown_relation")
                                continue 
                    except: pass
                    
                    # Hardening: Check for "Email Required"
                    try:
                        if page.locator(sel["email_input"]).is_visible(timeout=1000):
                            log("Email required for connection. Skipping.")
                            take_failure_screenshot(page, "email_required")
                            try: page.locator(sel["dismiss_modal"]).click()
                            except: pass
                            continue
                    except: pass

                    # Hardening: Check for Weekly Limit
                    try:
                        if page.get_by_text("weekly limit", exact=False).is_visible(timeout=1000):
                            log("CRITICAL: WEEKLY LIMIT REACHED. Stopping automation.")
                            take_failure_screenshot(page, "weekly_limit")
                            break
                    except: pass

                    # --- Handle connection modal ---
                    # Wait for any modal/overlay to appear after clicking Connect
                    random_sleep(1.5, 3)

                    # Detect what LinkedIn showed us after clicking Connect
                    modal_handled = False

                    if note:
                        # AI Personalized Note: Click "Add a note" and type it
                        try:
                            add_note_btn = None
                            # Try multiple selectors for "Add a note"
                            for add_sel in [
                                sel.get("add_note_btn", "button[aria-label='Add a note']"),
                                "button:has-text('Add a note')",
                                "button[aria-label='Add a note']",
                            ]:
                                try:
                                    btn = page.locator(add_sel).first
                                    if btn.is_visible(timeout=2000):
                                        add_note_btn = btn
                                        break
                                except: continue
                            
                            if add_note_btn:
                                add_note_btn.click()
                                random_sleep(0.5, 1)
                                
                                # Type the note with human-like delay
                                textarea = None
                                for ta_sel in [
                                    sel.get("note_textarea", "textarea[name='message']"),
                                    "textarea[name='message']",
                                    "textarea#custom-message",
                                    "textarea",
                                ]:
                                    try:
                                        ta = page.locator(ta_sel).first
                                        if ta.is_visible(timeout=2000):
                                            textarea = ta
                                            break
                                    except: continue
                                
                                if textarea:
                                    textarea.fill("")  # Clear default text
                                    # Type character by character for human feel
                                    for char in note:
                                        textarea.type(char, delay=random.randint(30, 80))
                                    random_sleep(0.5, 1)
                                    
                                    # Click Send
                                    send_btn = None
                                    for s_sel in [
                                        sel.get("send_btn", "button[aria-label='Send invitation']"),
                                        "button[aria-label='Send invitation']",
                                        "button[aria-label='Send now']",
                                        "button:has-text('Send')",
                                    ]:
                                        try:
                                            sb = page.locator(s_sel).first
                                            if sb.is_visible(timeout=2000):
                                                send_btn = sb
                                                break
                                        except: continue
                                    
                                    if send_btn:
                                        send_btn.click()
                                        log(f"SUCCESS: Connection request WITH NOTE sent to {url}")
                                        update_campaign_status(campaign_id, cid, "connection_sent")
                                        modal_handled = True
                                    else:
                                        log("Warning: Send button not found after typing note.")
                                        take_failure_screenshot(page, "send_btn_missing")
                                else:
                                    log("Warning: Note textarea not found. Will try sending without note.")
                                    try: page.locator(sel["dismiss_modal"]).click()
                                    except: pass
                            else:
                                log("'Add a note' button not found. Looking for 'Send without note'...")
                        except Exception as e:
                            log(f"Error during note flow: {e}. Will try sending without note.")
                            take_failure_screenshot(page, "note_error")

                    # Standard flow: Send without note (or fallback from note failure)
                    if not modal_handled:
                        send_now_btn = None
                        for sw_sel in [
                            sel.get("send_without_note_aria", "button[aria-label='Send without a note']"),
                            "button[aria-label='Send without a note']",
                            "button[aria-label='Send now']",
                            "button:has-text('Send without a note')",
                            "button:has-text('Send now')",
                        ]:
                            try:
                                sb = page.locator(sw_sel).first
                                if sb.is_visible(timeout=2000):
                                    send_now_btn = sb
                                    break
                            except: continue
                        
                        if send_now_btn:
                            log("Clicking 'Send without note'...")
                            send_now_btn.click()
                            log(f"SUCCESS: Connection request sent to {url}")
                            update_campaign_status(campaign_id, cid, "connection_sent")
                            modal_handled = True

                    # If still not handled, LinkedIn may have sent directly (no modal)
                    if not modal_handled:
                        # Check if Connect button disappeared (meaning it was sent)
                        random_sleep(1, 2)
                        connect_still_visible = False
                        try:
                            connect_still_visible = page.locator(sel["connect_btn_primary"]).is_visible(timeout=1000)
                        except: pass
                        
                        if not connect_still_visible:
                            # Check if Pending appeared
                            pending_visible = False
                            try:
                                pending_visible = page.locator("button", has_text="Pending").first.is_visible(timeout=1500)
                            except: pass
                            
                            if pending_visible:
                                log(f"SUCCESS: Connection sent directly (Pending badge confirmed) to {url}")
                            else:
                                log(f"Connection likely sent (Connect button gone) to {url}")
                            update_campaign_status(campaign_id, cid, "connection_sent")
                        else:
                            log(f"FAILED: Connect button still visible. Connection may NOT have been sent to {url}")
                            take_failure_screenshot(page, "connect_failed")
                            update_campaign_status(campaign_id, cid, "failed")

                random_sleep(2, 5)

            browser.close()
            log("AUTOMATION COMPLETE.")

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="JSON list of candidates {id, url, note}")
    parser.add_argument("--campaign_id", required=True, help="Campaign ID")
    args = parser.parse_args()
    
    candidates = json.loads(args.candidates)
    connect_to_profiles(candidates, args.campaign_id)
