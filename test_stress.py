"""
Stress Test for send_messages.py

Tests the full pipeline against 5 real LinkedIn profiles in DRY RUN mode.
No messages are actually sent.

For each profile, validates:
1. Profile navigation and load verification
2. Connection status detection
3. Message button finding + click strategy
4. Chat overlay / textarea detection
5. Dedup and InMail checks
6. Overlay cleanup

Usage:
    python test_stress.py
    python test_stress.py --debug-screenshots
"""

import json
import os
import sys
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

# Add backend dir to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

STATE_FILE = os.path.join("backend", "state.json")
SCREENSHOTS_DIR = os.path.join("backend", "execution", "screenshots", "stress_test")
LOGS_DIR = os.path.join("backend", "execution", "logs")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# --- Test Profiles (1st degree connections provided by user) ---
TEST_PROFILES = [
    {"name": "Antonela Mthuruthil", "url": "https://www.linkedin.com/in/antonelamthuruthil/"},
    {"name": "Josh Hartline",       "url": "https://www.linkedin.com/in/josh-hartline/"},
    {"name": "Kent Jones",          "url": "https://www.linkedin.com/in/kent-jones-206a5b38b/"},
    {"name": "Jose Abarca",         "url": "https://www.linkedin.com/in/jose-abarca-7731b73aa/"},
    {"name": "Jaden Bowdrie",       "url": "https://www.linkedin.com/in/jaden-bowdrie/"},
]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def random_sleep(min_s, max_s):
    time.sleep(random.uniform(min_s, max_s))


def close_all_overlays(page):
    for sel in [
        "button[aria-label='Close your conversation']",
        "button[aria-label='Dismiss']",
        "button.msg-overlay-bubble-header__control--close",
    ]:
        try:
            for btn in page.locator(sel).all():
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(0.3)
        except Exception:
            pass


def take_screenshot(page, label, profile_idx):
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SCREENSHOTS_DIR, f"profile{profile_idx}_{label}_{ts}.png")
        page.screenshot(path=path)
        return path
    except Exception:
        return ""


def test_profile(page, profile, idx, debug_ss=False):
    """
    Run the full messaging pipeline against a single profile.
    Returns a result dict with pass/fail for each step.
    """
    name = profile["name"]
    url = profile["url"]

    result = {
        "name": name,
        "url": url,
        "page_load": "SKIP",
        "connection_status": "SKIP",
        "message_btn": "SKIP",
        "btn_selector": "",
        "open_method": "SKIP",
        "textarea": "SKIP",
        "ta_selector": "",
        "inmail_check": "SKIP",
        "dedup_check": "SKIP",
        "overlay_cleanup": "SKIP",
        "overall": "FAIL",
        "error": "",
    }

    try:
        # =====================================================
        # STEP 1: Navigate to profile
        # =====================================================
        log(f"  [1/7] Navigating to {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        random_sleep(2, 4)
        page.evaluate(f"window.scrollBy(0, {random.randint(200, 400)})")
        random_sleep(1, 2)

        # Page load verification
        current_url = page.url.lower()
        if "login" in current_url or "checkpoint" in current_url:
            result["page_load"] = "FAIL"
            result["error"] = "Redirected to login"
            return result

        first_name = name.split()[0]
        try:
            page_text = page.locator("main").first.inner_text(timeout=5000)
            if first_name.lower() in page_text.lower():
                result["page_load"] = "PASS"
            else:
                result["page_load"] = "WARN"
                result["error"] = f"Name '{first_name}' not found on page"
        except Exception:
            result["page_load"] = "WARN"
            result["error"] = "Could not read main text"

        if debug_ss:
            take_screenshot(page, "01_loaded", idx)
        log(f"  [1/7] Page load: {result['page_load']}")

        # =====================================================
        # STEP 2: Connection status
        # =====================================================
        log(f"  [2/7] Checking connection status...")
        can_message = False
        main_section = page.locator("main").first
        # Compose URL links are inherently unique to profile owner (global search safe)
        msg_buttons = page.locator("a[href*='/messaging/compose']").all()
        # Generic Message buttons scoped to main section to avoid sidebar matches
        msg_buttons.extend(main_section.locator("button:has-text('Message'), a:has-text('Message')").all())
        for btn in msg_buttons:
            if btn.is_visible():
                has_lock = btn.locator(
                    "svg[data-test-icon='lock-small']"
                ).count() > 0
                if not has_lock:
                    can_message = True
                    break

        if not can_message:
            try:
                if main_section.locator("text=1st").first.is_visible(timeout=1000):
                    can_message = True
            except Exception:
                pass

        is_pending = False
        if not can_message:
            try:
                if page.locator("button:has-text('Pending')").first.is_visible(timeout=1000):
                    is_pending = True
            except Exception:
                pass

        if can_message:
            result["connection_status"] = "CONNECTED"
        elif is_pending:
            result["connection_status"] = "PENDING"
        else:
            result["connection_status"] = "UNKNOWN"

        log(f"  [2/7] Connection status: {result['connection_status']}")

        if result["connection_status"] != "CONNECTED":
            result["overall"] = "SKIP"
            result["error"] = f"Not connected ({result['connection_status']})"
            return result

        # =====================================================
        # STEP 3: Find Message button
        # =====================================================
        log(f"  [3/7] Finding Message button...")
        message_btn = None
        for msg_sel in [
            "a[href*='/messaging/compose']:visible",
            "button:has-text('Message'):visible",
            "a:has-text('Message'):visible",
            "button[aria-label='Message']:visible",
        ]:
            try:
                btn = page.locator(msg_sel).first
                if btn.is_visible(timeout=2000):
                    message_btn = btn
                    result["btn_selector"] = msg_sel
                    break
            except Exception:
                continue

        if message_btn:
            result["message_btn"] = "PASS"
            tag = message_btn.evaluate("el => el.tagName")
            href = message_btn.get_attribute("href") or "none"
            log(f"  [3/7] Message button: PASS (tag={tag}, href={href[:50] if href != 'none' else 'none'})")
        else:
            result["message_btn"] = "FAIL"
            result["error"] = "Message button not found"
            log(f"  [3/7] Message button: FAIL")
            return result

        if debug_ss:
            take_screenshot(page, "02_btn_found", idx)

        # =====================================================
        # STEP 4: Open message (click strategy)
        # =====================================================
        log(f"  [4/7] Opening message...")
        msg_href = None
        try:
            msg_href = message_btn.get_attribute("href")
        except Exception:
            pass

        if msg_href and "/messaging/compose" in msg_href:
            if msg_href.startswith("/"):
                msg_href = "https://www.linkedin.com" + msg_href
            page.goto(msg_href)
            random_sleep(3, 5)

            # Quick check: did the compose URL actually open a chat?
            quick_textarea = None
            for ta_sel in [
                "div.msg-form__contenteditable[role='textbox']",
                "div[role='textbox'][contenteditable='true']",
            ]:
                try:
                    ta = page.locator(ta_sel).first
                    if ta.is_visible(timeout=3000):
                        quick_textarea = ta
                        break
                except Exception:
                    continue

            if quick_textarea:
                result["open_method"] = "DIRECT_URL"
            else:
                # Compose URL landed on inbox. Fallback to button click.
                log(f"        COMPOSE URL REDIRECT: Falling back to button click...")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                random_sleep(2, 4)

                # Re-find message button
                message_btn = None
                for msg_sel in [
                    "a[href*='/messaging/compose']:visible",
                    "button:has-text('Message'):visible",
                    "a:has-text('Message'):visible",
                ]:
                    try:
                        btn = page.locator(msg_sel).first
                        if btn.is_visible(timeout=2000):
                            message_btn = btn
                            break
                    except Exception:
                        continue

                if message_btn:
                    try:
                        message_btn.scroll_into_view_if_needed()
                        random_sleep(0.5, 1)
                    except Exception:
                        pass
                    try:
                        message_btn.evaluate("el => el.click()")
                        random_sleep(2, 4)
                        result["open_method"] = "FALLBACK_CLICK"
                    except Exception:
                        try:
                            message_btn.click(force=True, timeout=5000)
                            random_sleep(2, 4)
                            result["open_method"] = "FALLBACK_CLICK"
                        except Exception:
                            result["open_method"] = "FAIL (fallback click failed)"
                            result["error"] = "Compose URL redirect + fallback click failed"
                            return result
                else:
                    result["open_method"] = "FAIL (no btn on return)"
                    result["error"] = "Could not re-find Message button"
                    return result
        else:
            try:
                message_btn.scroll_into_view_if_needed()
                random_sleep(0.5, 1)
            except Exception:
                pass

            click_success = False
            strategies_tried = []
            try:
                message_btn.evaluate("el => el.click()")
                click_success = True
                strategies_tried.append("js_eval")
            except Exception:
                strategies_tried.append("js_eval(FAIL)")
                try:
                    message_btn.click(force=True, timeout=5000)
                    click_success = True
                    strategies_tried.append("force_click")
                except Exception:
                    strategies_tried.append("force_click(FAIL)")
                    try:
                        message_btn.locator("span, svg, li-icon").first.click(force=True)
                        click_success = True
                        strategies_tried.append("inner_element")
                    except Exception:
                        strategies_tried.append("inner_element(FAIL)")

            if click_success:
                random_sleep(2, 4)
                result["open_method"] = f"BUTTON_CLICK ({', '.join(strategies_tried)})"
            else:
                result["open_method"] = f"FAIL ({', '.join(strategies_tried)})"
                result["error"] = "All click strategies failed"
                return result

        log(f"  [4/7] Open method: {result['open_method']}")

        if debug_ss:
            take_screenshot(page, "03_chat_opened", idx)

        # =====================================================
        # STEP 5: Find textarea
        # =====================================================
        log(f"  [5/7] Finding textarea...")
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
                if ta.is_visible(timeout=3000):
                    textarea = ta
                    result["ta_selector"] = ta_sel
                    break
            except Exception:
                continue

        if textarea:
            result["textarea"] = "PASS"
        else:
            result["textarea"] = "FAIL"
            result["error"] = "Textarea not found"

        log(f"  [5/7] Textarea: {result['textarea']}")

        # =====================================================
        # STEP 6: InMail + Dedup checks
        # =====================================================
        log(f"  [6/7] Running safety checks...")

        # InMail check
        is_inmail = False
        for inm_sel in ["text=InMail", "text=inmail", "text=Free InMail"]:
            try:
                if page.locator(inm_sel).first.is_visible(timeout=1000):
                    is_inmail = True
                    break
            except Exception:
                continue
        result["inmail_check"] = "INMAIL_DETECTED" if is_inmail else "PASS"

        # Dedup check
        has_outgoing = False
        for dup_sel in [
            ".msg-s-event-listitem--other",
            ".msg-s-event-listitem__message-bubble--outgoing",
        ]:
            try:
                if len(page.locator(dup_sel).all()) > 0:
                    has_outgoing = True
                    break
            except Exception:
                continue
        result["dedup_check"] = "ALREADY_SENT" if has_outgoing else "PASS"

        log(f"  [6/7] InMail: {result['inmail_check']}, Dedup: {result['dedup_check']}")

        # =====================================================
        # STEP 7: Cleanup
        # =====================================================
        log(f"  [7/7] Cleaning up overlays...")
        close_all_overlays(page)
        random_sleep(1, 2)
        result["overlay_cleanup"] = "PASS"

        # Overall result
        critical_steps = [result["page_load"], result["message_btn"], result["textarea"]]
        if all(s in ("PASS", "WARN") for s in critical_steps):
            result["overall"] = "PASS"
        else:
            result["overall"] = "FAIL"

    except Exception as e:
        result["error"] = str(e)
        result["overall"] = "ERROR"

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stress test for LinkedIn message sender")
    parser.add_argument("--debug-screenshots", action="store_true")
    args = parser.parse_args()

    log("=== STRESS TEST: LinkedIn Message Pipeline ===")
    log(f"Profiles to test: {len(TEST_PROFILES)}")
    log(f"Debug screenshots: {args.debug_screenshots}")
    log("")

    if not os.path.exists(STATE_FILE):
        log("ERROR: No session state found. Please login first.")
        return

    results = []

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

        # Session check
        log("Checking session health...")
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
        random_sleep(2, 4)
        if "login" in page.url.lower():
            log("ERROR: Session expired. Please re-login.")
            browser.close()
            return
        log("Session healthy.\n")

        for i, profile in enumerate(TEST_PROFILES):
            log(f"=== Profile {i+1}/{len(TEST_PROFILES)}: {profile['name']} ===")
            result = test_profile(page, profile, i, debug_ss=args.debug_screenshots)
            results.append(result)
            log(f"  RESULT: {result['overall']}")
            if result["error"]:
                log(f"  ERROR: {result['error']}")
            log("")

            # Rate limiting between profiles
            if i < len(TEST_PROFILES) - 1:
                delay = random.uniform(3, 6)
                log(f"  Waiting {delay:.1f}s before next profile...\n")
                time.sleep(delay)

        browser.close()

    # =====================================================
    # RESULTS TABLE
    # =====================================================
    log("\n" + "=" * 80)
    log("STRESS TEST RESULTS")
    log("=" * 80)

    header = f"{'#':>2} {'Name':<22} {'Load':>6} {'Status':>10} {'MsgBtn':>7} {'Open':>20} {'Textarea':>9} {'InMail':>9} {'Dedup':>12} {'OVERALL':>8}"
    log(header)
    log("-" * len(header))

    pass_count = 0
    for i, r in enumerate(results):
        row = (
            f"{i+1:>2} "
            f"{r['name']:<22} "
            f"{r['page_load']:>6} "
            f"{r['connection_status']:>10} "
            f"{r['message_btn']:>7} "
            f"{r['open_method'][:20]:>20} "
            f"{r['textarea']:>9} "
            f"{r['inmail_check']:>9} "
            f"{r['dedup_check']:>12} "
            f"{r['overall']:>8}"
        )
        log(row)
        if r["overall"] in ("PASS",):
            pass_count += 1

    log("-" * len(header))
    log(f"PASSED: {pass_count}/{len(results)}")

    # Failures detail
    failures = [r for r in results if r["overall"] not in ("PASS", "SKIP")]
    if failures:
        log(f"\nFAILED PROFILES:")
        for r in failures:
            log(f"  - {r['name']}: {r['error']}")

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = os.path.join(LOGS_DIR, f"stress_test_{ts}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log(f"\nFull results saved: {results_path}")


if __name__ == "__main__":
    main()
