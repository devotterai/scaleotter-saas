"""
Stress Test v2: Connection Detection + Messaging Pipeline

Tests 15 real LinkedIn profiles for:
  Phase A: Connection status detection (Connected / Not Connected / Pending)
  Phase B: Messaging pipeline (both Direct URL and Button Click methods)

Detection order (DISQUALIFIERS FIRST):
  1. "Pending" button visible?     → PENDING
  2. "Connect" button visible?     → NOT_CONNECTED
  3. "2nd"/"3rd" badge visible?    → NOT_CONNECTED
  4. "1st" badge visible?          → CONNECTED
  5. Message btn / compose URL?    → CONNECTED
  6. None of the above?            → UNKNOWN

Usage:
    python test_stress_v2.py
    python test_stress_v2.py --debug-screenshots
"""

import json
import os
import sys
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

STATE_FILE = os.path.join("backend", "state.json")
SCREENSHOTS_DIR = os.path.join("backend", "execution", "screenshots", "stress_v2")
LOGS_DIR = os.path.join("backend", "execution", "logs")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# --- 15 Test Profiles (mix of connected / not connected / unknown) ---
TEST_PROFILES = [
    {"name": "Jaden Bowdrie",        "url": "https://www.linkedin.com/in/jaden-bowdrie/"},
    {"name": "Shiro Zyrah Ndirangu", "url": "https://www.linkedin.com/in/shirozyrahndirangu/"},
    {"name": "Stéphane Godaire",     "url": "https://www.linkedin.com/in/sgodaire/"},
    {"name": "Charles Pinner",       "url": "https://www.linkedin.com/in/charles-pinner-494b24334/"},
    {"name": "Cameron Marion",       "url": "https://www.linkedin.com/in/cameron-marion-555523422344323324/"},
    {"name": "Nathan Derminio",      "url": "https://www.linkedin.com/in/nathanderminio/"},
    {"name": "James Merriam",        "url": "https://www.linkedin.com/in/james-merriam/"},
    {"name": "Christian Noyola",     "url": "https://www.linkedin.com/in/christian-noyola-7b8bb6239/"},
    {"name": "Juan Perez",           "url": "https://www.linkedin.com/in/juanperez88/"},
    {"name": "Lauren Sharpe",        "url": "https://www.linkedin.com/in/laurensharpe5414/"},
    {"name": "Hunter Lela",          "url": "https://www.linkedin.com/in/hunter-lela-0a2aa7332/"},
    {"name": "Mohamed Shehab",       "url": "https://www.linkedin.com/in/mshehab/"},
    {"name": "Lillian Fortunato",    "url": "https://www.linkedin.com/in/lillian-fortunato-a6b4163a9/"},
    {"name": "Ankit Sarkar",         "url": "https://www.linkedin.com/in/ankit-sarkar-5a02a2362/"},
    {"name": "Bill Gates",           "url": "https://www.linkedin.com/in/williamhgates/"},
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
        path = os.path.join(SCREENSHOTS_DIR, f"p{profile_idx:02d}_{label}_{ts}.png")
        page.screenshot(path=path)
        return path
    except Exception:
        return ""


# =====================================================
# PHASE A: CONNECTION DETECTION
# =====================================================
def detect_connection_status(page, name, idx, debug_ss=False):
    """
    Detect connection status using DISQUALIFIER-FIRST approach.

    CRITICAL: Button checks are scoped to the PROFILE HEADER SECTION
    (first <section> in <main>), NOT the entire <main> element.
    If no signals are found in the profile card, a broader fallback
    checks the entire page for text-based clues (e.g., "No connections found").

    Returns a dict with all signals and the final status.
    """
    main = page.locator("main").first
    # The profile header card = first <section> inside <main>
    profile_card = main.locator("section").first

    signals = {
        "pending_btn": False,
        "connect_btn": False,
        "degree_2nd": False,
        "degree_3rd": False,
        "degree_1st": False,
        "message_btn_main": False,
        "compose_url": False,
        "follow_btn": False,
        "following_btn": False,
        "no_common_connections": False,
        "status": "UNKNOWN",
    }

    # --- Signal 1: Pending button (scoped to profile card) ---
    try:
        pending = profile_card.locator("button:has-text('Pending')").first
        if pending.is_visible(timeout=1000):
            signals["pending_btn"] = True
    except Exception:
        pass

    # --- Signal 2: Connect button / link ---
    # LinkedIn A/B tests different element types for the Connect CTA:
    #   - <button> with text "Connect"
    #   - <a> link with text "Connect" and href containing /preload/custom-invite/
    # Scoped to profile card first, with fallback to page-wide name-specific selectors.
    try:
        first_name = name.split()[0] if name else ""

        # A) Profile card scope — check both <button> and <a> tags
        for sel in [
            "button:has-text('Connect')",
            "button[aria-label*='Connect']",
            "a:has-text('Connect')",
        ]:
            try:
                conn_el = profile_card.locator(sel).first
                if conn_el.is_visible(timeout=1000):
                    el_text = conn_el.inner_text(timeout=1000).strip().lower()
                    if el_text in ("connect", "+ connect"):
                        signals["connect_btn"] = True
                        break
            except Exception:
                continue

        # B) Invite URL pattern (globally unique to profile owner)
        if not signals["connect_btn"]:
            try:
                invite_link = profile_card.locator("a[href*='/preload/custom-invite/']").first
                if invite_link.is_visible(timeout=1000):
                    signals["connect_btn"] = True
            except Exception:
                pass

        # C) Fallback: name-specific aria-label (globally unique, safe page-wide)
        if not signals["connect_btn"] and first_name:
            try:
                named_btn = page.locator(f"button[aria-label*='Invite'][aria-label*='{first_name}']").first
                if named_btn.is_visible(timeout=1000):
                    signals["connect_btn"] = True
            except Exception:
                pass
    except Exception:
        pass

    # --- Signal 3: Degree badges (2nd, 3rd, 1st) from profile card text ---
    try:
        header_text = ""
        try:
            header_text = profile_card.inner_text(timeout=3000)
        except Exception:
            pass

        if header_text:
            if "· 2nd" in header_text or "\n2nd" in header_text:
                signals["degree_2nd"] = True
            elif "· 3rd" in header_text or "\n3rd" in header_text or "3rd+" in header_text.lower():
                signals["degree_3rd"] = True
            elif "· 1st" in header_text or "\n1st" in header_text:
                signals["degree_1st"] = True
    except Exception:
        pass

    # --- Signal 4: 1st degree badge (explicit span check) ---
    if not signals["degree_1st"]:
        try:
            spans = profile_card.locator("span.dist-value:has-text('1st')").all()
            if len(spans) > 0:
                signals["degree_1st"] = True
        except Exception:
            pass

    # --- Signal 5: Message button (scoped to profile card) ---
    try:
        msg_selectors = [
            "button:has-text('Message')",
            "a:has-text('Message')",
        ]
        for sel in msg_selectors:
            try:
                msg_btn = profile_card.locator(sel).first
                if msg_btn.is_visible(timeout=1000):
                    has_lock = msg_btn.locator("svg[data-test-icon='lock-small']").count() > 0
                    if not has_lock:
                        signals["message_btn_main"] = True
                        break
            except Exception:
                continue
    except Exception:
        pass

    # --- Signal 6: Compose URL link (scoped to profile card) ---
    try:
        compose = profile_card.locator("a[href*='/messaging/compose']").first
        if compose.is_visible(timeout=1000):
            signals["compose_url"] = True
    except Exception:
        pass

    # --- Signal 7: Follow button (scoped to profile card) ---
    try:
        follow_btn = profile_card.locator("button:has-text('Follow')").first
        if follow_btn.is_visible(timeout=1000):
            btn_text = follow_btn.inner_text(timeout=500).strip().lower()
            if btn_text in ("follow", "+ follow"):
                signals["follow_btn"] = True
    except Exception:
        pass

    # --- Signal 8: Following button (public figures — not connected) ---
    try:
        following_btn = profile_card.locator("button:has-text('Following')").first
        if following_btn.is_visible(timeout=1000):
            signals["following_btn"] = True
    except Exception:
        pass

    # --- Signal 9: "No connections found" / "no common connection" text ---
    # This appears on profiles where you have zero mutual connections
    # (usually public figures you're not connected to)
    try:
        page_text = main.inner_text(timeout=3000).lower()
        if "no connections found" in page_text or "no common connection" in page_text:
            signals["no_common_connections"] = True
    except Exception:
        pass

    # =====================================================
    # DECISION: Disqualifiers first, then qualifiers
    # =====================================================
    if signals["pending_btn"]:
        signals["status"] = "PENDING"

    elif signals["connect_btn"]:
        signals["status"] = "NOT_CONNECTED"

    elif signals["degree_2nd"] or signals["degree_3rd"]:
        signals["status"] = "NOT_CONNECTED"

    elif signals["degree_1st"]:
        signals["status"] = "CONNECTED"

    elif signals["message_btn_main"] and not signals["connect_btn"]:
        signals["status"] = "CONNECTED"

    elif signals["compose_url"] and not signals["connect_btn"] and not signals["degree_2nd"] and not signals["degree_3rd"]:
        signals["status"] = "CONNECTED"

    elif signals["following_btn"] or signals["follow_btn"]:
        # Following/Follow button without Message = not connected (public figure)
        signals["status"] = "NOT_CONNECTED"

    elif signals["no_common_connections"]:
        # Explicit "no common connection" text = not connected
        signals["status"] = "NOT_CONNECTED"

    else:
        signals["status"] = "UNKNOWN"

    return signals


# =====================================================
# PHASE B: MESSAGING PIPELINE (Direct URL + Button Click)
# =====================================================
def test_direct_url(page, profile, idx, debug_ss=False):
    """
    Test messaging via direct compose URL navigation.
    Returns: PASS, FAIL, or N/A
    """
    try:
        # Find compose URL link
        compose = page.locator("a[href*='/messaging/compose']").first
        if not compose.is_visible(timeout=2000):
            return "NO_URL", ""

        href = compose.get_attribute("href") or ""
        if not href or "/messaging/compose" not in href:
            return "NO_URL", ""

        if href.startswith("/"):
            href = "https://www.linkedin.com" + href

        # Navigate to compose URL
        page.goto(href)
        random_sleep(3, 5)

        # Check if textarea appeared
        for ta_sel in [
            "div.msg-form__contenteditable[role='textbox']",
            "div[role='textbox'][contenteditable='true']",
        ]:
            try:
                ta = page.locator(ta_sel).first
                if ta.is_visible(timeout=3000):
                    if debug_ss:
                        take_screenshot(page, "direct_url_ok", idx)
                    close_all_overlays(page)
                    return "PASS", ta_sel
            except Exception:
                continue

        if debug_ss:
            take_screenshot(page, "direct_url_fail", idx)
        close_all_overlays(page)
        return "FAIL", "textarea not found"

    except Exception as e:
        return "ERROR", str(e)


def test_button_click(page, profile, idx, debug_ss=False):
    """
    Test messaging via button click on profile page.
    Returns: PASS, FAIL, or N/A
    """
    url = profile["url"]
    try:
        # Navigate back to profile
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        random_sleep(2, 4)

        # Find message button in main section
        main = page.locator("main").first
        message_btn = None
        for sel in [
            "a[href*='/messaging/compose']",
            "button:has-text('Message')",
            "a:has-text('Message')",
        ]:
            try:
                btn = main.locator(sel).first
                if btn.is_visible(timeout=2000):
                    # Verify no lock
                    has_lock = btn.locator("svg[data-test-icon='lock-small']").count() > 0
                    if not has_lock:
                        message_btn = btn
                        break
            except Exception:
                continue

        if not message_btn:
            return "NO_BTN", ""

        # Scroll into view
        try:
            message_btn.scroll_into_view_if_needed()
            random_sleep(0.5, 1)
        except Exception:
            pass

        # Click using JS eval (most reliable)
        click_ok = False
        try:
            message_btn.evaluate("el => el.click()")
            click_ok = True
        except Exception:
            try:
                message_btn.click(force=True, timeout=5000)
                click_ok = True
            except Exception:
                pass

        if not click_ok:
            return "CLICK_FAIL", ""

        random_sleep(2, 4)

        # Check for textarea
        for ta_sel in [
            "div.msg-form__contenteditable[role='textbox']",
            "div[role='textbox'][contenteditable='true']",
            "div.msg-form__contenteditable",
        ]:
            try:
                ta = page.locator(ta_sel).first
                if ta.is_visible(timeout=3000):
                    if debug_ss:
                        take_screenshot(page, "btn_click_ok", idx)
                    close_all_overlays(page)
                    return "PASS", ta_sel
            except Exception:
                continue

        if debug_ss:
            take_screenshot(page, "btn_click_fail", idx)
        close_all_overlays(page)
        return "FAIL", "textarea not found"

    except Exception as e:
        return "ERROR", str(e)


# =====================================================
# MAIN TEST RUNNER
# =====================================================
def test_profile(page, profile, idx, debug_ss=False):
    """Full test for one profile: detection + messaging (if connected)."""
    name = profile["name"]
    url = profile["url"]

    result = {
        "name": name,
        "url": url,
        "page_load": "SKIP",
        "signals": {},
        "status": "UNKNOWN",
        "direct_url": "SKIP",
        "direct_url_detail": "",
        "btn_click": "SKIP",
        "btn_click_detail": "",
        "error": "",
    }

    try:
        # --- Navigate to profile ---
        log(f"  [1/4] Navigating to {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        random_sleep(2, 4)
        page.evaluate(f"window.scrollBy(0, {random.randint(100, 300)})")
        random_sleep(1, 2)

        # --- Page load check ---
        current_url = page.url.lower()
        if "login" in current_url or "checkpoint" in current_url:
            result["page_load"] = "LOGIN_REDIRECT"
            result["error"] = "Redirected to login page"
            return result
        if "/404" in current_url or "/error/" in current_url or "page-not-found" in current_url:
            result["page_load"] = "404"
            result["error"] = "Profile not found"
            return result
        # Check for invalid/redirected URLs
        if "/in/" not in current_url and "/pub/" not in current_url:
            result["page_load"] = "REDIRECT"
            result["error"] = f"Redirected to: {page.url}"
            return result

        result["page_load"] = "OK"

        if debug_ss:
            take_screenshot(page, "01_loaded", idx)

        # --- Phase A: Connection Detection ---
        log(f"  [2/4] Detecting connection status...")
        signals = detect_connection_status(page, name, idx, debug_ss)
        result["signals"] = signals
        result["status"] = signals["status"]

        log(f"  [2/4] Status: {signals['status']} "
            f"(pending={signals['pending_btn']}, connect={signals['connect_btn']}, "
            f"2nd={signals['degree_2nd']}, 3rd={signals['degree_3rd']}, "
            f"1st={signals['degree_1st']}, msg_btn={signals['message_btn_main']}, "
            f"compose={signals['compose_url']}, follow={signals['follow_btn']})")

        if debug_ss:
            take_screenshot(page, "02_status", idx)

        # --- Phase B: Messaging Pipeline (only if CONNECTED) ---
        if signals["status"] == "CONNECTED":
            # Test 1: Direct URL method
            log(f"  [3/4] Testing Direct URL method...")
            du_result, du_detail = test_direct_url(page, profile, idx, debug_ss)
            result["direct_url"] = du_result
            result["direct_url_detail"] = du_detail
            log(f"  [3/4] Direct URL: {du_result}")

            # Test 2: Button click method (navigate back to profile first)
            log(f"  [4/4] Testing Button Click method...")
            bc_result, bc_detail = test_button_click(page, profile, idx, debug_ss)
            result["btn_click"] = bc_result
            result["btn_click_detail"] = bc_detail
            log(f"  [4/4] Button Click: {bc_result}")
        else:
            log(f"  [3/4] Skipping Direct URL test (not connected)")
            log(f"  [4/4] Skipping Button Click test (not connected)")
            result["direct_url"] = "SKIP"
            result["btn_click"] = "SKIP"

        # Cleanup
        close_all_overlays(page)

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stress test v2: Connection detection + messaging")
    parser.add_argument("--debug-screenshots", action="store_true")
    args = parser.parse_args()

    log("=" * 70)
    log("STRESS TEST v2: Connection Detection + Messaging Pipeline")
    log("=" * 70)
    log(f"Profiles: {len(TEST_PROFILES)}")
    log(f"Debug screenshots: {args.debug_screenshots}")
    log("")

    if not os.path.exists(STATE_FILE):
        log("ERROR: No session state found. Run login first.")
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
            log(f"{'='*60}")
            log(f"Profile {i+1}/{len(TEST_PROFILES)}: {profile['name']}")
            log(f"{'='*60}")

            result = test_profile(page, profile, i, debug_ss=args.debug_screenshots)
            results.append(result)

            status_emoji = {
                "CONNECTED": "YES",
                "NOT_CONNECTED": "NO",
                "PENDING": "PEND",
                "UNKNOWN": "???",
            }.get(result["status"], "???")

            log(f"  RESULT: Status={status_emoji} | DirectURL={result['direct_url']} | BtnClick={result['btn_click']}")
            if result["error"]:
                log(f"  ERROR: {result['error']}")
            log("")

            # Rate limiting
            if i < len(TEST_PROFILES) - 1:
                delay = random.uniform(3, 6)
                log(f"  Waiting {delay:.1f}s...\n")
                time.sleep(delay)

        browser.close()

    # =====================================================
    # RESULTS TABLE
    # =====================================================
    print("\n")
    log("=" * 100)
    log("STRESS TEST v2 RESULTS")
    log("=" * 100)

    header = (
        f"{'#':>2} {'Name':<22} {'Load':>5} "
        f"{'Pend':>5} {'Conn':>5} {'2nd':>4} {'3rd':>4} {'1st':>4} "
        f"{'MsgBtn':>7} {'Compose':>8} {'Follow':>7} "
        f"{'STATUS':>15} {'DirectURL':>10} {'BtnClick':>10}"
    )
    log(header)
    log("-" * len(header))

    connected_count = 0
    not_connected_count = 0
    pending_count = 0
    unknown_count = 0

    for i, r in enumerate(results):
        s = r.get("signals", {})
        row = (
            f"{i+1:>2} {r['name']:<22} {r['page_load']:>5} "
            f"{'Y' if s.get('pending_btn') else '.':>5} "
            f"{'Y' if s.get('connect_btn') else '.':>5} "
            f"{'Y' if s.get('degree_2nd') else '.':>4} "
            f"{'Y' if s.get('degree_3rd') else '.':>4} "
            f"{'Y' if s.get('degree_1st') else '.':>4} "
            f"{'Y' if s.get('message_btn_main') else '.':>7} "
            f"{'Y' if s.get('compose_url') else '.':>8} "
            f"{'Y' if s.get('follow_btn') else '.':>7} "
            f"{r['status']:>15} {r['direct_url']:>10} {r['btn_click']:>10}"
        )
        log(row)

        if r["status"] == "CONNECTED":
            connected_count += 1
        elif r["status"] == "NOT_CONNECTED":
            not_connected_count += 1
        elif r["status"] == "PENDING":
            pending_count += 1
        else:
            unknown_count += 1

    log("-" * len(header))
    log(f"CONNECTED: {connected_count} | NOT_CONNECTED: {not_connected_count} | PENDING: {pending_count} | UNKNOWN: {unknown_count}")

    # Error details
    errors = [r for r in results if r["error"]]
    if errors:
        log(f"\nERRORS:")
        for r in errors:
            log(f"  - {r['name']}: {r['error']}")

    # Messaging results for connected profiles
    connected_results = [r for r in results if r["status"] == "CONNECTED"]
    if connected_results:
        log(f"\nMESSAGING PIPELINE (connected profiles only):")
        du_pass = sum(1 for r in connected_results if r["direct_url"] == "PASS")
        bc_pass = sum(1 for r in connected_results if r["btn_click"] == "PASS")
        log(f"  Direct URL: {du_pass}/{len(connected_results)} passed")
        log(f"  Button Click: {bc_pass}/{len(connected_results)} passed")

    # Save results
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = os.path.join(LOGS_DIR, f"stress_v2_{ts_str}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log(f"\nFull results saved: {results_path}")


if __name__ == "__main__":
    main()
