import requests
import json

def test_get_candidates():
    try:
        response = requests.get("http://localhost:8000/api/candidates")
        response.raise_for_status()
        candidates = response.json()
        
        print(f"Retrieved {len(candidates)} candidates.")
        if candidates:
            first = candidates[0]
            print(f"Name: {first.get('full_name')}")
            breakdown = first.get('experience_breakdown')
            print(f"Breakdown: {breakdown} (Type: {type(breakdown)})")
            
            if isinstance(breakdown, list):
                print("PASS: experience_breakdown is a list.")
            else:
                print(f"FAIL: experience_breakdown is {type(breakdown)}")

            # Check new fields
            edu = first.get('education')
            skills = first.get('skills')
            summary = first.get('summary')
            
            print(f"Education: {len(edu) if edu else 0} items")
            print(f"Skills: {len(skills) if skills else 0} items")
            print(f"Summary: {summary[:50] if summary else 'None'}")
            
            if edu and isinstance(edu, list):
                 print("PASS: education found.")
            else:
                 print("WARN: education missing or empty (might be expected for some)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_get_candidates()
