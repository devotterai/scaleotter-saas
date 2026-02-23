
import asyncio
from playwright.async_api import async_playwright
import json
import time

async def main():
    async with async_playwright() as p:
        # Launch browser with debugging visual
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            storage_state="backend/state.json",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to Profile...")
        await page.goto("https://www.linkedin.com/in/jarodwalker/", timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)
        
        print("\n=== TESTING TEXT PARSING EXTRACTION ===")
        try:
            # 1. Get full text of main content
            main_el = page.locator("main").first
            if await main_el.is_visible():
                full_text = await main_el.inner_text()
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                print(f"Total lines captured: {len(lines)}")
                
                # 2. Find the name
                name = "Jarod Walker"
                start_idx = -1
                
                # Fuzzy finding name in lines
                for i, line in enumerate(lines):
                    if name.lower() in line.lower():
                        print(f"  Found Name match at line {i}: '{line}'")
                        start_idx = i
                        break
                
                if start_idx != -1:
                    # 3. Look at next few lines for headline
                    # Skip "1st", "Pro", location, contact info
                    print("  Scanning subsequent lines for Headline...")
                    for i in range(start_idx + 1, min(start_idx + 10, len(lines))):
                        candidate = lines[i]
                        print(f"    Line {i}: '{candidate}'")
                        
                        # Heuristic: Length > 10, No numbers-only, Not "1st"
                        if len(candidate) > 5 and "1st" not in candidate and "Contact info" not in candidate and "United States" not in candidate:
                            print(f"  ✅ HEURISTIC MATCH: '{candidate}'")
                            break
                else:
                    print("  ❌ Name not found in main text.")
                    print(f"Dump first 20 lines: {lines[:20]}")
                    
        except Exception as e:
            print(f"Extraction failed: {e}")
            
        print("\nClosing in 5 seconds...")
        time.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
