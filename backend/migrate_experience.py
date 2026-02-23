import sqlite3
import os
import json
import sys

# Add local path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.experience_logic import calculate_relevant_experience

# Use absolute path to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "candidates.db")

# This is the query we used for the restore
QUERY = "Software Engineer in San Francisco"

def migrate():
    # Connect to root DB 
    ROOT_DB = os.path.join(BASE_DIR, "..", "candidates.db")
    if not os.path.exists(ROOT_DB):
        print(f"DB not found at {ROOT_DB}")
        return

    conn = sqlite3.connect(ROOT_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Add Column (ignore if exists)
    try:
        c.execute("ALTER TABLE candidates ADD COLUMN relevant_experience REAL")
        print("Added column 'relevant_experience'.")
    except sqlite3.OperationalError:
        print("Column 'relevant_experience' already exists.")

    # 2. Fetch All
    c.execute("SELECT * FROM candidates")
    rows = c.fetchall()
    
    print(f"Migrating {len(rows)} candidates...")
    
    updated = 0
    for row in rows:
        try:
            raw_data = json.loads(row['raw_data'])
            work_history = raw_data.get('work_history', [])
            
            # Recalculate based on the query that generated them
            # (In a real app, we'd store the query with the candidate or in a separate 'searches' table)
            # For this fix, we assume they match the current query context
            rel_exp = calculate_relevant_experience(work_history, QUERY)
            
            c.execute("UPDATE candidates SET relevant_experience = ? WHERE id = ?", (rel_exp, row['id']))
            updated += 1
        except Exception as e:
            print(f"Failed to update {row['id']}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Migration complete. Updated {updated} records.")

if __name__ == "__main__":
    migrate()
