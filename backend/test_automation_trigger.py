import requests
import sqlite3
import os

BASE_URL = "http://localhost:8000/api"
DB_PATH = os.path.join(os.path.dirname(__file__), "candidates.db")

def test_trigger():
    # 1. Ensure Campaign Exists
    print("Getting campaigns...")
    res = requests.get(f"{BASE_URL}/campaigns")
    campaigns = res.json()
    
    selected_campaign = None
    if campaigns:
         selected_campaign = campaigns[0]
         print(f"Using existing campaign: {selected_campaign['name']} ({selected_campaign['id']})")
    else:
         print("Creating test campaign...")
         res = requests.post(f"{BASE_URL}/campaigns", json={"name": "Automated Test Campaign"})
         selected_campaign = res.json()
         print(f"Created campaign: {selected_campaign['name']}")

    # 2. Ensure Candidate in Campaign
    print(f"Checking details for {selected_campaign['id']}...")
    res = requests.get(f"{BASE_URL}/campaigns/{selected_campaign['id']}")
    details = res.json()
    
    pending = [c for c in details if c.get("campaign_status") == "pending"]
    if not pending:
         print("No pending candidates. Adding one...")
         # Get any candidate
         res = requests.get(f"{BASE_URL}/candidates")
         candidates = res.json()
         if not candidates:
             print("No candidates in DB to add. Please source some first.")
             return
         
         candidate_to_add = candidates[0]
         print(f"Adding candidate {candidate_to_add['full_name']}...")
         requests.post(f"{BASE_URL}/campaigns/{selected_campaign['id']}/add", json={"candidate_id": candidate_to_add['id']})
    else:
         print(f"Found {len(pending)} pending candidates.")

    # 3. Trigger Automation
    print("Triggering automation...")
    try:
        res = requests.post(f"{BASE_URL}/campaigns/{selected_campaign['id']}/start")
        print(f"Response Status: {res.status_code}")
        print(f"Response Body: {res.json()}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_trigger()
