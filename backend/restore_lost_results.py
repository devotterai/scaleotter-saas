import requests
import json
import time

QUERY = "Software Engineer in San Francisco"
API_URL = "http://localhost:8000/api/source"

def restore():
    print(f"Restoring results for: '{QUERY}'...")
    
    payload = {
        "query": QUERY,
        "limit": 10
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        candidates = data.get("candidates", [])
        print(f"Successfully restored {len(candidates)} candidates.")
        
    except Exception as e:
        print(f"Restore failed: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")

if __name__ == "__main__":
    restore()
