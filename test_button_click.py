"""
Test: Direct Message Button Click Fallback
Simulates the fallback path in send_messages.py:
1. Visit Jarod Walker's profile
2. Find the blue Message button
3. Click it directly (NOT extracting href — testing the fallback)
4. Verify that a chat overlay opens with a textarea
"""
import asyncio
from playwright.async_api import async_playwright
import time

TARGET_URL = "https://www.linkedin.com/in/jarodwalker/"
TARGET_NAME = "Jarod Walker"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            storage_state="backend/state.json",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"=== TEST: Direct Button Click Fallback ===")
        print(f"Target: {TARGET_NAME} ({TARGET_URL})")
        
        # 1. Navigate to profile
        print("\n[STEP 1] Navigating to profile...")
        try:
            await page.goto(TARGET_URL, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"  Navigation error (retrying): {e}")
            time.sleep(2)
            await page.goto(TARGET_URL, timeout=30000)
        time.sleep(4)
        print("  Profile loaded.")
        
        # 2. Find the Message button (same selectors as send_messages.py)
        print("\n[STEP 2] Finding Message button...")
        message_btn = None
        for msg_sel in [
            "a[href*='/messaging/compose']:visible",
            "button:has-text('Message'):visible",
            "a:has-text('Message'):visible",
            "button[aria-label='Message']:visible",
        ]:
            try:
                btn = page.locator(msg_sel).first
                if await btn.is_visible(timeout=2000):
                    tag = await btn.evaluate("el => el.tagName")
                    href = await btn.get_attribute("href") or "none"
                    text = await btn.inner_text()
                    print(f"  FOUND via '{msg_sel}'")
                    print(f"    Tag: {tag}, Text: '{text}', Href: {href[:60] if href != 'none' else 'none'}")
                    message_btn = btn
                    break
            except:
                continue
        
        if not message_btn:
            print("  ERROR: No Message button found!")
            time.sleep(5)
            await browser.close()
            return
        
        # 3. FALLBACK: Click the button directly (NOT using href)
        print("\n[STEP 3] Clicking Message button directly (FALLBACK PATH)...")
        
        # Scroll into view
        try:
            await message_btn.scroll_into_view_if_needed()
            time.sleep(1)
        except:
            pass
        
        # Try clicking
        click_success = False
        try:
            await message_btn.click(timeout=5000)
            click_success = True
            print("  Click strategy 1 (normal click): SUCCESS")
        except Exception as e:
            print(f"  Click strategy 1 failed: {e}")
            try:
                await message_btn.evaluate("el => el.click()")
                click_success = True
                print("  Click strategy 2 (JS eval): SUCCESS")
            except Exception as e2:
                print(f"  Click strategy 2 failed: {e2}")
                try:
                    await message_btn.locator("span, svg, li-icon").first.click(force=True)
                    click_success = True
                    print("  Click strategy 3 (inner element): SUCCESS")
                except Exception as e3:
                    print(f"  Click strategy 3 failed: {e3}")
        
        if not click_success:
            print("  ERROR: All click strategies failed!")
            time.sleep(5)
            await browser.close()
            return
        
        time.sleep(3)
        print("  Waiting for chat overlay...")
        
        # 4. Check for textarea (same selectors as send_messages.py)
        print("\n[STEP 4] Looking for message textarea...")
        textarea = None
        for ta_sel in [
            "div.msg-form__contenteditable[role='textbox']",
            "div[role='textbox'][aria-label='Write a message\u2026']",
            "div[role='textbox'][contenteditable='true']",
            "div.msg-form__contenteditable",
            "div[aria-label='Write a message\u2026']",
            "div[aria-placeholder='Write a message\u2026']",
            ".msg-form__message-texteditor div[role='textbox']",
        ]:
            try:
                ta = page.locator(ta_sel).first
                if await ta.is_visible(timeout=3000):
                    textarea = ta
                    print(f"  FOUND via '{ta_sel}'")
                    break
            except:
                continue
        
        if textarea:
            print("\n✅ SUCCESS: Chat overlay opened with textarea!")
            print("   The direct button click fallback WORKS.")
            print("   Message would be typed here and sent.")
        else:
            print("\n❌ FAIL: Textarea not found after clicking.")
            # Check if a "Type a name" search modal appeared instead
            try:
                search_input = page.locator("input[placeholder='Type a name or multiple names']").first
                if await search_input.is_visible(timeout=2000):
                    print("   A 'New message' search modal appeared instead of a direct chat.")
                    print("   This means the button click opened a compose window, not a direct chat.")
                else:
                    print("   No search modal either. Unknown state.")
            except:
                print("   No search modal either. Unknown state.")
        
        print("\nClosing in 5 seconds...")
        time.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
