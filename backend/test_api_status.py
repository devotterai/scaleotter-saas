import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test():
    # 1. List campaigns to get ID
    r = requests.get(f"{BASE_URL}/api/campaigns")
    campaigns = r.json()
    if not campaigns:
        print("No campaigns found.")
        return

    cid = campaigns[0]["id"]
    print(f"Checking Campaign {cid}...")

    # 2. Get details
    r = requests.get(f"{BASE_URL}/api/campaigns/{cid}")
    details = r.json()
    
    print(json.dumps(details, indent=2))

    # 3. Find Nicholas Fowler
    found = False
    for c in details:
        if "fowler" in str(c).lower(): # Search in whole object
            print(f"Found Candidate: {c.get('name')}")
            print(f"Status: {c.get('campaign_status')}")
            found = True
            
    if not found:
        print("Candidate 'fowler' NOT found in response.")

if __name__ == "__main__":
    test()
