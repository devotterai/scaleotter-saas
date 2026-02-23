import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api"

def test_persistence():
    # 1. Trigger source (limit=1)
    print("1. Sourcing one candidate...")
    source_payload = {"query": "Product Manager in New York", "limit": 1}
    try:
        res = requests.post(f"{API_URL}/source", json=source_payload)
        res.raise_for_status()
        print("   Sourcing complete.")
    except Exception as e:
        print(f"   Sourcing failed: {e}")
        return

    # 2. Check DB
    print("2. Checking /api/candidates...")
    try:
        res = requests.get(f"{API_URL}/candidates")
        res.raise_for_status()
        candidates = res.json()
        print(f"   Retrieved {len(candidates)} saved candidates.")
        
        if len(candidates) > 0:
            latest = candidates[0]
            print(f"   Latest: {latest.get('full_name')} - {latest.get('ai_score')}")
            print(f"   Reasoning: {latest.get('ai_reasoning')[:50]}...")
            print("   No candidates found in DB!")
            
    except Exception as e:
        print(f"   DB check failed: {e}")
        if 'res' in locals():
             print(f"   Response Text: {res.text}")

if __name__ == "__main__":
    test_persistence()
