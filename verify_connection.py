from playwright.sync_api import sync_playwright
import json
import os
import time

# Attempt to find state.json
STATE_PATH = os.path.join("backend", "state.json")
if not os.path.exists(STATE_PATH):
    STATE_PATH = "state.json"
if not os.path.exists(STATE_PATH):
    # Try absolute path based on known layout
    STATE_PATH = r"c:\Users\MrRul\OneDrive\Desktop\OtterAI\backend\state.json"

print(f"Using state file: {STATE_PATH}")

def run():
    with sync_playwright() as p:
        # Launch headless=False to see what's happening
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context(storage_state=STATE_PATH)
        except Exception as e:
            print(f"Error loading state: {e}")
            return

        page = context.new_page()
        
        url = "https://www.linkedin.com/in/jarodwalker/"
        print(f"Navigating to {url}...")
        page.goto(url)
        
        try:
            page.wait_for_selector("h1", timeout=15000) # Wait for name usually
        except:
            print("Timed out waiting for h1")
        
        print("--- DEBUGGING CONNECTION STATUS ---")
        
        # 1. Search for generic "1st" text
        print("\n[Searching for '1st' text]")
        elements = page.locator("text=1st").all()
        print(f"Found {len(elements)} elements with text=1st")
        for i, el in enumerate(elements):
            try:
                if el.is_visible():
                    html = el.evaluate("el => el.outerHTML")
                    print(f"  #{i} (Visible): {html}")
                else:
                    print(f"  #{i} (Hidden)")
            except:
                pass

        # 2. Search for degree badge specifically (span with visual confirmation)
        print("\n[Searching for specific badge classes]")
        for selector in ["span.dist-value", ".artdeco-entity-lockup__degree", ".dist-value", "span.pv-top-card--list-bullet"]:
            count = page.locator(selector).count()
            print(f"Selector '{selector}': found {count}")
            if count > 0:
                 print(f"  HTML: {page.locator(selector).first.evaluate('el => el.outerHTML')}")

        # 3. Check for specific text patterns in the top card
        print("\n[Checking Top Card content]")
        try:
            top_card = page.locator(".pv-top-card").first
            if top_card.count() > 0:
                text = top_card.inner_text()
                print(f"Top Card Text length: {len(text)}")
                if "1st" in text:
                    print("  '1st' found in Top Card text!")
                else:
                     print("  '1st' NOT found in Top Card text.")
        except:
            print("Could not analyze top card")

        # 4. Check for Message button
        print("\n[Checking Buttons]")
        msg_btns = page.locator("button:has-text('Message')").all()
        for i, btn in enumerate(msg_btns):
            if btn.is_visible():
                print(f"  Message Btn #{i}: Visible")
                # Check for lock icon (InMail)
                if btn.locator("svg[data-test-icon='lock-small']").count() > 0:
                     print("    -> Has Lock Icon (InMail/Premium)")
                else:
                     print("    -> No Lock Icon")

        # --- TEST NEW LOGIC ---
        print("\n[TESTING NEW LOGIC]")
        can_message = False
        
        # 1. Message Button Check
        msg_buttons = page.locator("button:has-text('Message')").all()
        for btn in msg_buttons:
            if btn.is_visible():
                has_lock = btn.locator("svg[data-test-icon='lock-small']").count() > 0
                if not has_lock:
                    can_message = True
                    print("LOGIC: Connected (Found Message Button with NO lock)")
                    break
        
        # 2. 1st Degree Text Check
        if not can_message:
            try:
                if page.locator("text=1st").first.is_visible():
                    can_message = True
                    print("LOGIC: Connected (Found '1st' text)")
            except:
                pass
                
        if can_message:
            print("FINAL DECISION: CONNECTED (Ready for messaging)")
        else:
            print("FINAL DECISION: NOT CONNECTED (Pending or blocked)")

            # 2a. Attempt to Extract Headline (Text Parsing - Most Robust)
            print("\n[TESTING HEADLINE EXTRACTION - TEXT PARSING]")
            headline = ""
            
            try:
                # 1. Get full text of main content
                main_el = page.locator("main").first
                if main_el.is_visible():
                    full_text = main_el.inner_text()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    # 2. Find the name
                    name = "Jarod Walker"
                    try:
                        name_idx = lines.index(name)
                        # 3. The headline is usually the next line
                        if name_idx + 1 < len(lines):
                            candidate_headline = lines[name_idx + 1]
                            
                            # Sanity check: ensure it's not "1st" or "Pro" badge text
                            if "1st" in candidate_headline or len(candidate_headline) < 3:
                                if name_idx + 2 < len(lines):
                                    candidate_headline = lines[name_idx + 2]
                            
                            headline = candidate_headline
                            print(f"  Parsed Headline: '{headline}'")
                    except ValueError:
                        print(f"  Name '{name}' not found in main text lines.")
                        # Debug: print first 10 lines
                        print(f"  First 10 lines: {lines[:10]}")
            except Exception as e:
                print(f"Text parsing failed: {e}")

        # 3. Test Clicking Message Button
        if can_message:
            print("\n[TESTING CLICK ACTION]")
            # Find the best candidate button to click
            # We want the main "Message" button, usually "button:has-text('Message')"
            candidates = page.locator("a[href*='/messaging/compose'], button:has-text('Message'), a:has-text('Message')").all()
            clicked = False
            for btn in candidates:
                if btn.is_visible():
                    print(f"  Found Message Button/Link: {btn}")
                    href = btn.get_attribute("href")
                    if href:
                         print(f"  Has HREF: {href}")
                    # Check if it has lock
                    if btn.locator("svg[data-test-icon='lock-small']").count() > 0:
                        print("  Skipping LOCKED button")
                        continue
                    
                    print(f"  Attempting to INTERACT with: {btn}")
                    
                    # NEW TEST: Extract HREF and Navigate
                    href = btn.get_attribute("href")
                    if href and "/messaging/compose" in href:
                        # Fix relative URLs
                        if href.startswith("/"):
                            href = "https://www.linkedin.com" + href
                            
                        print(f"  Found Secure Message URL: {href}")
                        print("  [TEST] Navigating to URL directly...")
                        try:
                            page.goto(href)
                            print("  Navigation initiated. Waiting for page load...")
                            time.sleep(5)
                            if "messaging/thread" in page.url or "messaging/compose" in page.url:
                                print("  SUCCESS: Navigated to messaging context.")
                                
                                # 4. Verify Active Chat Name (Crucial for robust search)
                                print("\n[TESTING CHAT VERIFICATION]")
                                chat_title = ""
                                for title_sel in [
                                    "h2.msg-entity-lockup__entity-title",
                                    ".msg-entity-lockup__entity-title",
                                    "div.msg-entity-lockup__entity-title",
                                    "a.msg-thread-tile__profile-link"
                                ]:
                                    try:
                                        el = page.locator(title_sel).first
                                        if el.is_visible():
                                            chat_title = el.inner_text().strip()
                                            break
                                    except: continue
                                
                                print(f"  Active Chat Title: '{chat_title}'")
                                
                                clicked = True
                                break
                            else:
                                print(f"  WARNING: URL is now {page.url}")
                        except Exception as e:
                            print(f"  Navigation failed: {e}")
                            
                    else:
                         print("  No secure HREF found. Attempting standard click as fallback...")
                         try:
                            btn.click(timeout=3000)
                            clicked = True
                            print("  CLICK SUCCESSFUL!")
                            time.sleep(3) 
                            break
                         except Exception as e:
                            print(f"  Click failed: {e}")
            
            if not clicked:
                print("  Could not interact with any Message button.")

        browser.close()

if __name__ == "__main__":
    run()
