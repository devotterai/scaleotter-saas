import asyncio
from playwright.async_api import async_playwright
import os
import random
import time
import json
import sys

# Load state
STATE_FILE = os.path.join("backend", "state.json")

async def main():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(storage_state=STATE_FILE)
        page = await context.new_page()
        
        print("=== TESTING SEARCH RELIABILITY ===")
        
        # 1. Go to Messaging Page directly (Simulate "New Message" flow)
        print("Navigating to Messaging...")
        try:
            await page.goto("https://www.linkedin.com/messaging/", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Navigation warning: {e}")
        time.sleep(5)
        
        # 2. Click "Compose" (Pencil Icon)
        print("Opening Compose Window...")
        try:
             # Selector for the "Compose message" icon in left rail
            compose_btn = page.locator("a[href*='/messaging/compose']").first
            if await compose_btn.is_visible():
                await compose_btn.click()
            else:
                print("Compose button not found via href. Trying generic...")
                await page.locator("svg[data-test-icon='compose-small']").first.click()
        except Exception as e:
            print(f"Error opening compose: {e}")
            return

        time.sleep(2)
        
        # 3. Test Candidate Name
        test_name = "Jarod Walker"
        print(f"Searching for: {test_name}")
        
        # 4. Find Search Input
        search_input = page.locator("input[placeholder='Type a name or multiple names']").first
        if await search_input.is_visible():
            await search_input.click()
            await search_input.fill(test_name)
            time.sleep(3) # Wait for suggestions
            
            # Select first result
            print("Selecting first result...")
            await page.keyboard.press("ArrowDown")
            time.sleep(0.5)
            await page.keyboard.press("Enter")
            time.sleep(3)
            
            # 5. VERIFY CHAT HEADER (Forensic Link Dump)
            print("\n[VERIFICATION STEP - FORENSIC DUMP]")
            chat_href = ""
            target_id = "jarodwalker"
            
            try:
                print("Scanning all links on page...")
                all_links = page.locator("a").all()
                count = len(await all_links)
                print(f"Found {count} links.")
                
                # Check first 200 links to avoid spam, or filter by 'in/'
                found_match = False
                for i, link in enumerate(await all_links):
                    if i > 500: break
                    try:
                        href = await link.get_attribute("href")
                        if href and "/in/" in href:
                            print(f"  LINK #{i}: {href}")
                            if target_id in href:
                                print(f"    -> MATCH FOUND! {href}")
                                found_match = True
                                chat_href = href
                    except: pass
                
                if found_match:
                     print("  EXACT MATCH: Found link to target profile!")
                else:
                    print("  NO MATCH found in any link.")
                    
            except Exception as e:
                print(f"Verification error: {e}")
            
            if chat_href:
                 print(f"  RESULT: VERIFIED URL ({chat_href})")
            else:
                 print("  RESULT: MISMATCH / NOT FOUND")
                
        else:
            print("Search input not found.")

        print("\nClosing in 5 seconds...")
        time.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
