import sys
import os
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright

def source_candidates(search_url):
    """
    Navigates to a LinkedIn search URL and scrapes the visible candidates.
    Returns a list of dicts: { name, headline, location, profile_url, summary }
    """
    candidates = []
    
    with sync_playwright() as p:
        # Launch visible browser (so user can see it happening)
        browser = p.chromium.launch(headless=False)
        
        # Load the saved session state (from login_linkedin.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        state_path = os.path.join(backend_dir, "state.json")
        
        if not os.path.exists(state_path):
            print(json.dumps({"error": "No login state found. Please login first."}))
            return

        context = browser.new_context(storage_state=state_path)
        page = context.new_page()
        
        try:
            print(f"DEBUG: Navigating to {search_url}", file=sys.stderr)
            page.goto(search_url)
            
            # Wait for results container
            page.wait_for_selector(".reusable-search__result-container", timeout=15000)
            
            # Scroll down to trigger lazy loading
            for i in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(1)
            
            # Scrape the cards
            results = page.query_selector_all(".reusable-search__result-container")
            
            for card in results:
                try:
                    # Extract Name
                    name_el = card.query_selector(".entity-result__title-text a span[aria-hidden='true']")
                    name = name_el.inner_text().strip() if name_el else "Unknown"
                    
                    # Extract Profile URL
                    link_el = card.query_selector(".entity-result__title-text a")
                    profile_url = link_el.get_attribute("href") if link_el else ""
                    if profile_url and "linkedin.com" not in profile_url:
                        profile_url = f"https://www.linkedin.com{profile_url}"

                    # Extract Headline (Job Title)
                    headline_el = card.query_selector(".entity-result__primary-subtitle")
                    headline = headline_el.inner_text().strip() if headline_el else ""
                    
                    # Extract Location
                    loc_el = card.query_selector(".entity-result__secondary-subtitle")
                    location = loc_el.inner_text().strip() if loc_el else ""

                    # Basic filtering (avoid "LinkedIn Member" anonymity)
                    if name != "LinkedIn Member":
                        candidates.append({
                            "name": name,
                            "headline": headline,
                            "location": location,
                            "profile_url": profile_url
                        })
                        
                except Exception as e:
                    # extensive error handling per card so one failure doesn't kill the batch
                    print(f"DEBUG: Error parsing card: {e}", file=sys.stderr)
                    continue

            # Return JSON to stdout
            print(json.dumps(candidates))
            
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        finally:
            browser.close()

if __name__ == "__main__":
    # Expecting search_url as first argument
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        source_candidates(target_url)
    else:
        # Fallback/Test URL
        # "Software Engineer in Austin"
        test_url = "https://www.linkedin.com/search/results/people/?keywords=software%20engineer%20austin&origin=CLUSTER_EXPANSION&sid=TyW"
        source_candidates(test_url)
