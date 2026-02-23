import sys
import os

# Add project root to sys.path
import importlib.util

# Load database.py directly to avoid 'backend' package conflict
DB_PATH = os.path.join(os.path.dirname(__file__), "database.py")
spec = importlib.util.spec_from_file_location("local_db", DB_PATH)
db_module = importlib.util.module_from_spec(spec)
sys.modules["local_db"] = db_module
spec.loader.exec_module(db_module)

init_db = db_module.init_db
save_candidate = db_module.save_candidate
get_all_candidates = db_module.get_all_candidates
DB_NAME = db_module.DB_NAME
import datetime

print(f"DB_NAME resolved to: {DB_NAME}")

def test():
    print("Initializing DB...")
    init_db()
    
    if os.path.exists(DB_NAME):
        print("DB file created successfully.")
    else:
        print("DB file NOT found!")
        
    print("Saving test candidate...")
    c = {
        "id": "test_id_123",
        "full_name": "Test User",
        "headline": "Tester",
        "company": "TestCorp",
        "location": "TestCity",
        "linkedin_url": "http://linkedin.com/in/test",
        "years_experience": 5.5,
        "ai_score": 99,
        "ai_reasoning": "Excellent test subject.",
        "skills": ["Testing", "DB"]
    }
    save_candidate(c)
    
    print("Retrieving candidates...")
    candidates = get_all_candidates()
    print(f"Retrieved {len(candidates)} candidates.")
    for cand in candidates:
        print(f" - {cand['full_name']}")

if __name__ == "__main__":
    test()
