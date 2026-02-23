import sqlite3
import os
import json

# Use absolute path to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "candidates.db")

def dump_last_payload():
    # Connect
    # Connect to root DB only
    DB_NAME = os.path.join(BASE_DIR, "..", "candidates.db")
    if not os.path.exists(DB_NAME):
        print(f"Database not found at {DB_NAME}")
        return

    conn = sqlite3.connect(DB_NAME)

    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get latest candidate
    c.execute("SELECT raw_data FROM candidates ORDER BY created_at DESC LIMIT 1")
    row = c.fetchone()
    
    if row:
        payload = json.loads(row['raw_data'])
        print(json.dumps(payload, indent=2))
    else:
        print("No candidates found.")

    conn.close()

if __name__ == "__main__":
    dump_last_payload()
