"""
DOM Inspection: Find hidden Pending signals on Lillian's profile.
The "Pending" state is hidden behind the More (3-dot) menu.
"""
import json
import os
import time
from playwright.sync_api import sync_playwright

STATE_FILE = os.path.join("backend", "state.json")
URL = "https://www.linkedin.com/in/lillian-fortunato-a6b4163a9/"
OUTPUT_DIR = os.path.join("backend", "execution", "screenshots", "dom_inspect")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=STATE_FILE,
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    """)
    page = context.new_page()

    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    if "login" in page.url.lower():
        print("ERROR: Session expired"); browser.close(); exit(1)

    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)
    page.evaluate("window.scrollBy(0, 200)")
    time.sleep(2)

    # Screenshot before clicking More
    page.screenshot(path=os.path.join(OUTPUT_DIR, "lillian_before_more.png"))

    main = page.locator("main").first
    profile_card = main.locator("section").first

    # =============================================
    # CHECK 1: What buttons are in the profile card?
    # =============================================
    print("=== PROFILE CARD BUTTONS ===")
    all_btns = profile_card.locator("button").all()
    for i, btn in enumerate(all_btns):
        try:
            text = btn.inner_text(timeout=500).strip()
            aria = btn.get_attribute("aria-label") or ""
            vis = btn.is_visible()
            print(f"  [{i}] text='{text}' aria-label='{aria}' visible={vis}")
        except:
            print(f"  [{i}] (error)")

    # =============================================
    # CHECK 2: What links are in the profile card?
    # =============================================
    print("\n=== PROFILE CARD LINKS ===")
    all_links = profile_card.locator("a").all()
    for i, link in enumerate(all_links[:20]):
        try:
            text = link.inner_text(timeout=500).strip()[:50]
            href = link.get_attribute("href") or ""
            vis = link.is_visible()
            if text or href:
                print(f"  [{i}] text='{text}' href='{href[:80]}' visible={vis}")
        except:
            pass

    # =============================================
    # CHECK 3: Full profile card text (look for degree, pending, etc.)
    # =============================================
    print("\n=== PROFILE CARD TEXT ===")
    try:
        text = profile_card.inner_text(timeout=3000)
        print(text[:500])
    except Exception as e:
        print(f"Error: {e}")

    # =============================================
    # CHECK 4: Click the More button and look for Pending/Withdraw
    # =============================================
    print("\n=== CLICKING MORE BUTTON ===")
    try:
        # Find the More/3-dot button
        more_btn = None
        for sel in [
            "button[aria-label='More']",
            "button[aria-label*='More actions']",
            "button[aria-label*='more']",
        ]:
            try:
                btn = profile_card.locator(sel).first
                if btn.is_visible(timeout=1000):
                    more_btn = btn
                    print(f"Found More button via: {sel}")
                    break
            except:
                continue

        if more_btn:
            more_btn.click()
            time.sleep(2)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "lillian_more_menu.png"))

            # Look at the dropdown menu items
            dropdown = page.evaluate("""() => {
                // Check for dropdown/popover/menu items
                const dropdowns = document.querySelectorAll('[role="menu"], [role="listbox"], .artdeco-dropdown__content, .artdeco-dropdown__content-inner');
                const results = [];
                for (const dd of dropdowns) {
                    const items = dd.querySelectorAll('[role="menuitem"], li, button, a, div[tabindex]');
                    for (const item of items) {
                        const text = item.innerText ? item.innerText.trim() : '';
                        if (text) {
                            results.push({
                                text: text.substring(0, 100),
                                tag: item.tagName,
                                ariaLabel: item.getAttribute('aria-label') || '',
                                className: (item.className || '').substring(0, 80)
                            });
                        }
                    }
                }
                return results;
            }""")
            print(f"Dropdown items: {len(dropdown)}")
            for item in dropdown:
                print(f"  [{item['tag']}] {item['text']}")

            # Also check for ANY element with "Pending" or "Withdraw" text
            pending_check = page.evaluate("""() => {
                const allElements = document.querySelectorAll('*');
                const results = [];
                for (const el of allElements) {
                    const ownText = Array.from(el.childNodes)
                        .filter(n => n.nodeType === Node.TEXT_NODE)
                        .map(n => n.textContent.trim())
                        .join(' ');
                    if (ownText.toLowerCase().includes('pending') || 
                        ownText.toLowerCase().includes('withdraw')) {
                        results.push({
                            tag: el.tagName,
                            text: ownText.substring(0, 100),
                            visible: el.offsetParent !== null || el.offsetHeight > 0,
                            className: (el.className || '').substring(0, 60)
                        });
                    }
                }
                return results;
            }""")
            print(f"\nElements with 'Pending' or 'Withdraw' text: {len(pending_check)}")
            for item in pending_check:
                print(f"  [{item['tag']}] '{item['text']}' visible={item['visible']}")

            # Close the dropdown
            page.keyboard.press("Escape")
            time.sleep(1)
        else:
            print("Could not find More button!")
    except Exception as e:
        print(f"Error with More button: {e}")

    # =============================================
    # CHECK 5: Look for hidden Pending indicators in the DOM
    # =============================================
    print("\n=== HIDDEN PENDING INDICATORS ===")
    hidden_pending = page.evaluate("""() => {
        // Check for aria-labels mentioning pending/withdraw/invitation
        const results = [];
        const allElements = document.querySelectorAll('[aria-label]');
        for (const el of allElements) {
            const label = el.getAttribute('aria-label').toLowerCase();
            if (label.includes('pending') || label.includes('withdraw') || 
                label.includes('invitation') || label.includes('invite')) {
                results.push({
                    tag: el.tagName,
                    ariaLabel: el.getAttribute('aria-label'),
                    text: (el.innerText || '').trim().substring(0, 50),
                    visible: el.offsetParent !== null
                });
            }
        }
        return results;
    }""")
    for item in hidden_pending:
        print(f"  [{item['tag']}] aria-label='{item['ariaLabel']}' text='{item['text']}' visible={item['visible']}")

    # =============================================
    # CHECK 6: Check if there's a degree badge at all
    # =============================================
    print("\n=== DEGREE BADGE CHECK ===")
    degree_check = page.evaluate("""() => {
        const main = document.querySelector('main');
        const section = main ? main.querySelector('section') : null;
        if (!section) return 'No section found';
        const text = section.innerText;
        return {
            has_1st: text.includes('1st'),
            has_2nd: text.includes('2nd'),
            has_3rd: text.includes('3rd'),
            has_degree_any: /\b(1st|2nd|3rd)\b/.test(text),
        };
    }""")
    print(json.dumps(degree_check, indent=2))

    browser.close()
    print("\n=== DONE ===")
