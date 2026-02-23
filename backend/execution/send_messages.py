"""
send_messages.py — Playwright automation for sending personalized LinkedIn messages.

For each candidate:
1. Visit their profile
2. If "Message" button visible -> accepted -> open message box -> type message -> send
3. If "Pending" visible -> not yet accepted -> skip
4. If neither -> likely declined -> mark as declined

Reliability features:
- --dry-run       : Does everything except actually sending (safe for testing)
- --debug-screenshots : Takes screenshots at every decision point
- Structured JSON audit log (logs/msg_run_{ts}.jsonl)
- DOM snapshot on failure (logs/dom_{id}_{ts}.html)
- Page load verification with retry
- Retry with backoff on click/textarea failures
- Overlay cleanup after every candidate
- Dedup detection (skips if already messaged)
- InMail detection (skips Premium-only contacts)
- Anti-detection spacing with human breaks
- Profile 404/redirect handling
"""

import argparse
import json
import os
import sys
import time
import random
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright

# Add backend dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import update_campaign_status, update_candidate_message, init_db

# Ensure tables exist (subprocess runs outside FastAPI)
init_db()

# --- Configuration ---
SELECTORS_FILE = os.path.join(os.path.dirname(__file__), "selectors.json")
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# --- Globals set by CLI args ---
DRY_RUN = False
DEBUG_SCREENSHOTS = False
AUDIT_LOG_PATH = None


# =====================================================================
# UTILITIES
# =====================================================================

def log(msg):
    """Print a timestamped message to console."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = "[DRY RUN] " if DRY_RUN else ""
    print(f"[{timestamp}] {prefix}{msg}")


def random_sleep(min_s, max_s):
    """Sleep for a random duration between min_s and max_s."""
    time.sleep(random.uniform(min_s, max_s))


def audit(candidate_id, candidate_name, step, result, selector="", duration_ms=0, screenshot_path="", error=""):
    """Append a structured JSON record to the audit log."""
    if not AUDIT_LOG_PATH:
        return
    record = {
        "timestamp": datetime.now().isoformat(),
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "step": step,
        "selector": selector,
        "result": result,
        "duration_ms": duration_ms,
        "screenshot_path": screenshot_path,
        "error": str(error) if error else "",
        "dry_run": DRY_RUN,
    }
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def take_screenshot(page, label, candidate_id="general"):
    """Take a screenshot and return the path. Works in both debug and failure modes."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        subdir = os.path.join(SCREENSHOTS_DIR, candidate_id[:12] if candidate_id else "general")
        os.makedirs(subdir, exist_ok=True)
        path = os.path.join(subdir, f"{label}_{ts}.png")
        page.screenshot(path=path)
        log(f"Screenshot: {path}")
        return path
    except Exception:
        return ""


def debug_screenshot(page, label, candidate_id="general"):
    """Take a screenshot ONLY if --debug-screenshots is enabled."""
    if DEBUG_SCREENSHOTS:
        return take_screenshot(page, label, candidate_id)
    return ""


def save_dom_snapshot(page, candidate_id, label):
    """Save page HTML to disk for offline debugging."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(LOGS_DIR, f"dom_{candidate_id[:8]}_{label}_{ts}.html")
        html = page.content()
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log(f"DOM snapshot saved: {path}")
        return path
    except Exception:
        return ""


def load_selectors():
    try:
        with open(SELECTORS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def close_all_overlays(page):
    """Ensure no message overlays are left open from previous interactions."""
    close_selectors = [
        "button[aria-label='Close your conversation']",
        "button[aria-label='Dismiss']",
        "button.msg-overlay-bubble-header__control--close",
    ]
    for sel in close_selectors:
        try:
            buttons = page.locator(sel).all()
            for btn in buttons:
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(0.3)
        except Exception:
            pass


def verify_profile_loaded(page, name, url):
    """
    Verify the profile page actually loaded by checking:
    1. URL didn't redirect to login/error
    2. Candidate's name appears somewhere on the page
    Returns (success: bool, reason: str)
    """
    current_url = page.url.lower()

    # Check for login redirect
    if "login" in current_url or "checkpoint" in current_url:
        return False, "Redirected to login page (session expired?)"

    # Check for 404/error pages
    if "404" in current_url or "/error/" in current_url:
        return False, "Profile not found (404)"

    # Check URL didn't redirect to a completely different profile
    # Extract slug from expected URL
    expected_slug = url.rstrip("/").split("/in/")[-1].lower() if "/in/" in url else ""
    if expected_slug and expected_slug not in current_url.lower():
        return False, f"URL redirected away from expected profile (now at {page.url})"

    # Check candidate's name appears on page (loose check)
    try:
        first_name = name.split()[0] if name else ""
        if first_name and len(first_name) > 2:
            page_text = page.locator("main").first.inner_text(timeout=5000)
            if first_name.lower() not in page_text.lower():
                return False, f"Name '{first_name}' not found on page"
    except Exception:
        # If we can't read main text, the page might not have loaded
        return False, "Could not read page content"

    return True, "Profile loaded successfully"


def check_dedup(page):
    """
    Check if we already sent a message in this conversation.
    Returns True if a recent outgoing message is detected.
    """
    try:
        # Look for outgoing message bubbles (messages from "you")
        # LinkedIn marks outgoing messages differently in the chat
        outgoing_selectors = [
            ".msg-s-event-listitem--other .msg-s-message-group__meta",
            ".msg-s-event-listitem__message-bubble--outgoing",
            ".msg-s-message-list-content .msg-s-event-listitem--other",
        ]
        for sel in outgoing_selectors:
            try:
                msgs = page.locator(sel).all()
                if len(msgs) > 0:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def check_inmail(page):
    """
    Check if the compose window is an InMail (requires credits).
    Returns True if InMail is detected.
    """
    try:
        inmail_indicators = [
            "text=InMail",
            "text=inmail",
            "text=Free InMail",
            ".premium-attribute",
            "text=InMail credit",
        ]
        for sel in inmail_indicators:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=1000):
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# =====================================================================
# MAIN AUTOMATION
# =====================================================================

def send_messages_to_profiles(candidates, campaign_id):
    """
    For each candidate:
    - Visit their LinkedIn profile
    - Check if "Message" button is visible (accepted connection)
    - If accepted: click Message, type the personalized message, send it
    - If "Pending": skip (not yet accepted)
    - If neither: mark as declined
    """
    global AUDIT_LOG_PATH
    sel = load_selectors()

    # Initialize audit log
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    AUDIT_LOG_PATH = os.path.join(LOGS_DIR, f"msg_run_{ts}.jsonl")

    log(f"=== MESSAGE SENDING AUTOMATION ===")
    log(f"Campaign: {campaign_id}")
    log(f"Candidates to process: {len(candidates)}")
    if DRY_RUN:
        log("MODE: DRY RUN (no messages will be sent)")
    if DEBUG_SCREENSHOTS:
        log("MODE: Debug screenshots enabled")
    log(f"Audit log: {AUDIT_LOG_PATH}")

    if not os.path.exists(STATE_FILE):
        log("ERROR: No session state found. Please login first.")
        return

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                storage_state=STATE_FILE,
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Stealth
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """)

            page = context.new_page()

            # --- SESSION HEALTH CHECK ---
            log("Checking session health...")
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            random_sleep(2, 4)

            if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                log("ERROR: Session expired. Please re-login.")
                audit("", "", "session_check", "FAIL", error="Session expired")
                browser.close()
                return

            log("Session is healthy.")
            audit("", "", "session_check", "OK")

            sent_count = 0
            skipped_count = 0
            declined_count = 0
            failed_count = 0

            for i, candidate in enumerate(candidates):
                url = candidate.get("url", "")
                cid = candidate.get("id", f"unknown_{i}")
                message = candidate.get("message", "")
                name = candidate.get("name", "Unknown")
                step_start = time.time()

                log(f"\n--- [{i+1}/{len(candidates)}] Processing: {name} ---")
                log(f"URL: {url}")

                if not url or not message:
                    log(f"Skipping: missing URL or message.")
                    audit(cid, name, "validation", "SKIP", error="Missing URL or message")
                    continue

                # --- ANTI-DETECTION: Human break every 5 messages ---
                if i > 0 and i % 5 == 0:
                    pause_secs = random.randint(30, 60)
                    log(f"ANTI-DETECTION: Taking a {pause_secs}s human break...")
                    audit(cid, name, "human_break", "OK", duration_ms=pause_secs * 1000)
                    time.sleep(pause_secs)

                # --- OVERLAY CLEANUP: Close any leftover overlays ---
                close_all_overlays(page)

                try:
                    # =========================================================
                    # STEP 1: NAVIGATE TO PROFILE
                    # =========================================================
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    random_sleep(2, 4)

                    # Scroll down a bit to look human
                    page.evaluate(f"window.scrollBy(0, {random.randint(200, 400)})")
                    random_sleep(1, 2)

                    # --- PAGE LOAD VERIFICATION ---
                    loaded, reason = verify_profile_loaded(page, name, url)
                    if not loaded:
                        log(f"PAGE LOAD FAIL: {reason}")
                        audit(cid, name, "page_load", "FAIL", error=reason)

                        # Retry once with backoff
                        log("Retrying page load in 5s...")
                        random_sleep(4, 6)
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        random_sleep(3, 5)
                        loaded, reason = verify_profile_loaded(page, name, url)

                        if not loaded:
                            log(f"PAGE LOAD FAIL (retry): {reason}")
                            take_screenshot(page, "page_load_fail", cid)
                            save_dom_snapshot(page, cid, "page_load_fail")
                            audit(cid, name, "page_load_retry", "FAIL", error=reason)
                            failed_count += 1
                            continue

                    log(f"Profile loaded: {name}")
                    ss = debug_screenshot(page, "01_profile_loaded", cid)
                    audit(cid, name, "page_load", "OK", screenshot_path=ss)

                    # =========================================================
                    # STEP 2: CHECK CONNECTION STATUS (Disqualifier-First)
                    # =========================================================
                    # Scope button checks to the profile header card (first
                    # <section> in <main>), NOT the entire page. The sidebar
                    # "More profiles for you" has Connect/Message buttons for
                    # OTHER people that would cause false positives.
                    can_message = False
                    is_pended = False
                    connection_status = "UNKNOWN"

                    main_section = page.locator("main").first
                    profile_card = main_section.locator("section").first

                    # --- Signal 1: Pending button (scoped to profile card) ---
                    sig_pending = False
                    try:
                        pending_btn = profile_card.locator("button:has-text('Pending')").first
                        if pending_btn.is_visible(timeout=1000):
                            sig_pending = True
                    except Exception:
                        pass

                    # --- Signal 2: Connect button / link (profile card + fallbacks) ---
                    # LinkedIn A/B tests different element types for Connect CTA:
                    #   - <button> with text "Connect"
                    #   - <a> link with text "Connect" and href /preload/custom-invite/
                    sig_connect = False
                    try:
                        first_name = name.split()[0] if name else ""
                        # A) Profile card scope — check <button> and <a> tags
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
                                        sig_connect = True
                                        break
                            except Exception:
                                continue
                        # B) Invite URL pattern (globally unique to profile owner)
                        if not sig_connect:
                            try:
                                invite_link = profile_card.locator("a[href*='/preload/custom-invite/']").first
                                if invite_link.is_visible(timeout=1000):
                                    sig_connect = True
                            except Exception:
                                pass
                        # C) Fallback: name-specific aria-label (globally unique, safe page-wide)
                        if not sig_connect and first_name:
                            try:
                                named = page.locator(f"button[aria-label*='Invite'][aria-label*='{first_name}']").first
                                if named.is_visible(timeout=1000):
                                    sig_connect = True
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # --- Signal 3: Degree badges from profile card text ---
                    sig_2nd = False
                    sig_3rd = False
                    sig_1st = False
                    try:
                        header_text = profile_card.inner_text(timeout=3000)
                        if "· 2nd" in header_text or "\n2nd" in header_text:
                            sig_2nd = True
                        elif "· 3rd" in header_text or "\n3rd" in header_text or "3rd+" in header_text.lower():
                            sig_3rd = True
                        elif "· 1st" in header_text or "\n1st" in header_text:
                            sig_1st = True
                    except Exception:
                        pass
                    # Explicit span check for 1st degree
                    if not sig_1st:
                        try:
                            if profile_card.locator("span.dist-value:has-text('1st')").count() > 0:
                                sig_1st = True
                        except Exception:
                            pass

                    # --- Signal 4: Message button (scoped to profile card) ---
                    sig_message = False
                    try:
                        for sel in ["button:has-text('Message')", "a:has-text('Message')"]:
                            try:
                                msg_btn = profile_card.locator(sel).first
                                if msg_btn.is_visible(timeout=1000):
                                    has_lock = msg_btn.locator("svg[data-test-icon='lock-small']").count() > 0
                                    if not has_lock:
                                        sig_message = True
                                        break
                            except Exception:
                                continue
                    except Exception:
                        pass

                    # --- Signal 5: Compose URL (scoped to profile card) ---
                    sig_compose = False
                    try:
                        compose = profile_card.locator("a[href*='/messaging/compose']").first
                        if compose.is_visible(timeout=1000):
                            sig_compose = True
                    except Exception:
                        pass

                    # --- Signal 6: Follow / Following button ---
                    sig_follow = False
                    sig_following = False
                    try:
                        fb = profile_card.locator("button:has-text('Follow')").first
                        if fb.is_visible(timeout=1000):
                            ft = fb.inner_text(timeout=500).strip().lower()
                            if ft in ("follow", "+ follow"):
                                sig_follow = True
                            elif ft == "following":
                                sig_following = True
                    except Exception:
                        pass
                    if not sig_following:
                        try:
                            fb2 = profile_card.locator("button:has-text('Following')").first
                            if fb2.is_visible(timeout=1000):
                                sig_following = True
                        except Exception:
                            pass

                    # --- Signal 7: "No connections found" text ---
                    sig_no_common = False
                    try:
                        pt = main_section.inner_text(timeout=3000).lower()
                        if "no connections found" in pt or "no common connection" in pt:
                            sig_no_common = True
                    except Exception:
                        pass

                    # --- DECISION (disqualifiers first, then qualifiers) ---
                    if sig_pending:
                        connection_status = "PENDING"
                        is_pended = True
                    elif sig_connect:
                        connection_status = "NOT_CONNECTED"
                    elif sig_2nd or sig_3rd:
                        connection_status = "NOT_CONNECTED"
                    elif sig_1st:
                        connection_status = "CONNECTED"
                        can_message = True
                    elif sig_message and not sig_connect:
                        connection_status = "CONNECTED"
                        can_message = True
                    elif sig_compose and not sig_connect and not sig_2nd and not sig_3rd:
                        connection_status = "CONNECTED"
                        can_message = True
                    elif sig_following or sig_follow:
                        connection_status = "NOT_CONNECTED"
                    elif sig_no_common:
                        connection_status = "NOT_CONNECTED"
                    else:
                        connection_status = "UNKNOWN"

                    log(f"CONNECTION: {name} → {connection_status} "
                        f"(pend={sig_pending}, conn={sig_connect}, "
                        f"2nd={sig_2nd}, 3rd={sig_3rd}, 1st={sig_1st}, "
                        f"msg={sig_message}, compose={sig_compose}, "
                        f"follow={sig_follow}, following={sig_following})")
                    debug_screenshot(page, "02_connection_status", cid)

                    if is_pended and not can_message:
                        log(f"PENDING: {name} has pending request. Skipping.")
                        debug_screenshot(page, "status_pending", cid)
                        audit(cid, name, "connection_status", "PENDING")
                        skipped_count += 1
                        continue

                    if connection_status == "NOT_CONNECTED":
                        log(f"DECLINED: {name} -- Not connected.")
                        audit(cid, name, "connection_status", "NOT_CONNECTED")
                        update_campaign_status(campaign_id, cid, "declined")
                        declined_count += 1
                        continue

                    if connection_status == "UNKNOWN":
                        log(f"UNKNOWN: {name} -- No clear connection signals found.")
                        take_screenshot(page, "status_unknown", cid)
                        save_dom_snapshot(page, cid, "status_unknown")
                        audit(cid, name, "connection_status", "UNKNOWN")
                        failed_count += 1
                        continue

                    # =========================================================
                    # STEP 3: FIND MESSAGE BUTTON (only reached if CONNECTED)
                    # =========================================================
                    message_btn = None
                    matched_selector = ""
                    # Search profile card first, then page-wide compose URL
                    for msg_sel in [
                        "a[href*='/messaging/compose']",
                        "button:has-text('Message')",
                        "a:has-text('Message')",
                    ]:
                        try:
                            btn = profile_card.locator(msg_sel).first
                            if btn.is_visible(timeout=2000):
                                has_lock = btn.locator("svg[data-test-icon='lock-small']").count() > 0
                                if not has_lock:
                                    message_btn = btn
                                    matched_selector = msg_sel
                                    break
                        except Exception:
                            continue

                    # Page-wide fallback for compose URL (always unique to profile owner)
                    if not message_btn:
                        try:
                            btn = page.locator("a[href*='/messaging/compose']").first
                            if btn.is_visible(timeout=2000):
                                message_btn = btn
                                matched_selector = "a[href*='/messaging/compose'] (page-wide)"
                        except Exception:
                            pass

                    if not message_btn:
                        log(f"WARN: {name} is CONNECTED but no Message button found. Skipping.")
                        take_screenshot(page, "connected_no_btn", cid)
                        audit(cid, name, "find_message_btn", "FAIL", error="Connected but no button")
                        failed_count += 1
                        continue

                    log(f"ACCEPTED: {name} -- Message button found via '{matched_selector}'.")
                    ss = debug_screenshot(page, "02_message_btn_found", cid)
                    audit(cid, name, "find_message_btn", "OK", selector=matched_selector, screenshot_path=ss)

                    # =========================================================
                    # STEP 4: OPEN MESSAGE (Direct Nav or Button Click)
                    # =========================================================
                    msg_href = None
                    try:
                        msg_href = message_btn.get_attribute("href")
                    except Exception:
                        pass

                    open_method = ""
                    if msg_href and "/messaging/compose" in msg_href:
                        # PRIMARY: Navigate directly via profileUrn URL
                        if msg_href.startswith("/"):
                            msg_href = "https://www.linkedin.com" + msg_href
                        log(f"PRIMARY: Navigating to compose URL...")
                        page.goto(msg_href)
                        random_sleep(3, 5)

                        # Quick check: did the compose URL actually open a chat?
                        # Sometimes it redirects to the messaging inbox without opening a conversation.
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
                            open_method = "direct_url"
                        else:
                            # Compose URL landed on inbox without opening chat.
                            # Fallback: go back to profile and click the button.
                            log(f"COMPOSE URL REDIRECT: No chat opened. Falling back to button click...")
                            audit(cid, name, "compose_url_redirect", "FALLBACK")
                            page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            random_sleep(2, 4)

                            # Re-find the message button
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
                                    open_method = "fallback_button_click"
                                except Exception:
                                    try:
                                        message_btn.click(force=True, timeout=5000)
                                        random_sleep(2, 4)
                                        open_method = "fallback_button_click"
                                    except Exception as e:
                                        log(f"ERROR: Fallback button click also failed: {e}")
                                        take_screenshot(page, "fallback_click_fail", cid)
                                        audit(cid, name, "fallback_click", "FAIL", error=str(e))
                                        failed_count += 1
                                        continue
                            else:
                                log(f"ERROR: Could not re-find Message button on return to profile.")
                                take_screenshot(page, "refind_btn_fail", cid)
                                audit(cid, name, "refind_message_btn", "FAIL")
                                failed_count += 1
                                continue
                    else:
                        # FALLBACK: Click the Message button on the profile
                        log(f"FALLBACK: Clicking Message button directly on profile...")

                        try:
                            message_btn.scroll_into_view_if_needed()
                            random_sleep(0.5, 1)
                        except Exception:
                            pass

                        # Click — JS eval first (normal click blocked by Sales Navigator SVG overlap)
                        click_success = False
                        click_error = ""
                        try:
                            message_btn.evaluate("el => el.click()")
                            click_success = True
                        except Exception as e1:
                            click_error = str(e1)
                            try:
                                message_btn.click(force=True, timeout=5000)
                                click_success = True
                            except Exception as e2:
                                click_error = str(e2)
                                try:
                                    message_btn.locator("span, svg, li-icon").first.click(force=True)
                                    click_success = True
                                except Exception as e3:
                                    click_error = str(e3)

                        if not click_success:
                            log(f"ERROR: All click strategies failed for {name}.")
                            take_screenshot(page, "click_fail", cid)
                            save_dom_snapshot(page, cid, "click_fail")
                            audit(cid, name, "click_message_btn", "FAIL", error=click_error)
                            failed_count += 1
                            continue

                        random_sleep(2, 4)
                        open_method = "button_click"

                    log(f"Chat opened via {open_method}.")
                    audit(cid, name, "open_message", "OK", selector=open_method)

                    # =========================================================
                    # STEP 5: FIND TEXTAREA (with retry)
                    # =========================================================
                    textarea = None
                    textarea_selector = ""
                    ta_selectors = [
                        "div.msg-form__contenteditable[role='textbox']",
                        "div[role='textbox'][aria-label='Write a message\u2026']",
                        "div[role='textbox'][contenteditable='true']",
                        "div.msg-form__contenteditable",
                        "div[aria-label='Write a message\u2026']",
                        "div[aria-placeholder='Write a message\u2026']",
                        ".msg-form__message-texteditor div[role='textbox']",
                    ]

                    for attempt in range(2):  # Try twice
                        for ta_sel in ta_selectors:
                            try:
                                ta = page.locator(ta_sel).first
                                if ta.is_visible(timeout=3000):
                                    textarea = ta
                                    textarea_selector = ta_sel
                                    break
                            except Exception:
                                continue
                        if textarea:
                            break
                        if attempt == 0:
                            log("Textarea not found. Retrying in 3s...")
                            audit(cid, name, "find_textarea", "RETRY")
                            random_sleep(2, 4)

                    if not textarea:
                        log(f"ERROR: Message compose box not found for {name}.")
                        take_screenshot(page, "no_textarea", cid)
                        save_dom_snapshot(page, cid, "no_textarea")
                        audit(cid, name, "find_textarea", "FAIL")
                        failed_count += 1
                        close_all_overlays(page)
                        continue

                    ss = debug_screenshot(page, "03_chat_opened", cid)
                    audit(cid, name, "find_textarea", "OK", selector=textarea_selector, screenshot_path=ss)
                    log(f"VERIFIED: Chat opened via {open_method} for {name}.")

                    # =========================================================
                    # STEP 5b: INMAIL DETECTION
                    # =========================================================
                    if check_inmail(page):
                        log(f"INMAIL: {name} requires InMail credits. Skipping.")
                        debug_screenshot(page, "inmail_detected", cid)
                        audit(cid, name, "inmail_check", "INMAIL")
                        skipped_count += 1
                        close_all_overlays(page)
                        continue

                    # =========================================================
                    # STEP 5c: DEDUP CHECK
                    # =========================================================
                    if check_dedup(page):
                        log(f"DEDUP: Already messaged {name}. Skipping.")
                        debug_screenshot(page, "dedup_detected", cid)
                        audit(cid, name, "dedup_check", "ALREADY_SENT")
                        skipped_count += 1
                        close_all_overlays(page)
                        continue

                    # =========================================================
                    # STEP 6: TYPE & SEND MESSAGE
                    # =========================================================
                    if DRY_RUN:
                        log(f"DRY RUN: Would send to {name}: \"{message[:80]}...\"")
                        ss = debug_screenshot(page, "04_dry_run", cid)
                        audit(cid, name, "send_message", "DRY_RUN", screenshot_path=ss)
                        sent_count += 1
                        close_all_overlays(page)
                        random_sleep(2, 4)
                        continue

                    # Click into the text area
                    textarea.click()
                    random_sleep(0.5, 1)

                    # Type message character by character for human feel
                    log(f"Typing message ({len(message)} chars)...")
                    for char in message:
                        textarea.type(char, delay=random.randint(25, 70))

                    random_sleep(1, 2)
                    ss = debug_screenshot(page, "04_message_typed", cid)
                    audit(cid, name, "type_message", "OK", screenshot_path=ss)

                    # Click Send
                    send_btn = None
                    for s_sel in [
                        sel.get("msg_send_btn", "button[aria-label='Send']"),
                        "button[aria-label='Send']",
                        "button.msg-form__send-button",
                        "button[type='submit']",
                    ]:
                        try:
                            sb = page.locator(s_sel).first
                            if sb.is_visible(timeout=2000):
                                send_btn = sb
                                break
                        except Exception:
                            continue

                    if send_btn:
                        send_btn.click()
                        random_sleep(1, 2)
                        elapsed = int((time.time() - step_start) * 1000)
                        log(f"SUCCESS: Message sent to {name} ({elapsed}ms)")
                        ss = debug_screenshot(page, "05_message_sent", cid)
                        audit(cid, name, "send_message", "SENT", duration_ms=elapsed, screenshot_path=ss)
                        update_campaign_status(campaign_id, cid, "message_sent")
                        update_candidate_message(campaign_id, cid, message, "sent")
                        sent_count += 1
                    else:
                        log(f"ERROR: Send button not found for {name}.")
                        take_screenshot(page, "no_send_btn", cid)
                        save_dom_snapshot(page, cid, "no_send_btn")
                        audit(cid, name, "send_message", "FAIL", error="Send button not found")
                        failed_count += 1

                    # =========================================================
                    # STEP 7: CLEANUP
                    # =========================================================
                    close_all_overlays(page)

                    # Anti-detection: variable delay between messages
                    delay = random.uniform(5, 12)
                    log(f"Waiting {delay:.1f}s before next candidate...")
                    time.sleep(delay)

                except Exception as e:
                    elapsed = int((time.time() - step_start) * 1000)
                    log(f"ERROR processing {name}: {e}")
                    take_screenshot(page, "error", cid)
                    save_dom_snapshot(page, cid, "error")
                    audit(cid, name, "unhandled_error", "FAIL", duration_ms=elapsed, error=traceback.format_exc())
                    failed_count += 1
                    close_all_overlays(page)
                    continue

            # =========================================================
            # SUMMARY
            # =========================================================
            log(f"\n=== AUTOMATION COMPLETE ===")
            log(f"Sent: {sent_count}")
            log(f"Skipped (pending/dedup/inmail): {skipped_count}")
            log(f"Declined: {declined_count}")
            log(f"Failed: {failed_count}")
            log(f"Audit log: {AUDIT_LOG_PATH}")

            audit("", "", "summary", "COMPLETE", error=json.dumps({
                "sent": sent_count, "skipped": skipped_count,
                "declined": declined_count, "failed": failed_count
            }))

            browser.close()

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        audit("", "", "critical_error", "FAIL", error=traceback.format_exc())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Message Sender with reliability features")
    parser.add_argument("--candidates", required=True, help="JSON list of candidates {id, url, message, name}")
    parser.add_argument("--campaign_id", required=True, help="Campaign ID")
    parser.add_argument("--dry-run", action="store_true", help="Do everything except actually send messages")
    parser.add_argument("--debug-screenshots", action="store_true", help="Take screenshots at every step")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    DEBUG_SCREENSHOTS = args.debug_screenshots

    candidates = json.loads(args.candidates)
    send_messages_to_profiles(candidates, args.campaign_id)
