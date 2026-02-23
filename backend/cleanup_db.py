import sqlite3
import os

# Use absolute path (same as database.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "..", "candidates.db")

def cleanup():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM candidates WHERE full_name = 'Test User'")
    print(f"Deleted {c.rowcount} test candidates.")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    cleanup()
