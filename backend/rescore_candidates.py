import sqlite3
import os
import json
import sys

# Add local path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_helper import score_candidate
from datetime import datetime

# Use absolute path to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "candidates.db")

# This is the context they were found in
JOB_DESCRIPTION = "Software Engineer in San Francisco"

def rescore():
    # Connect to root DB 
    ROOT_DB = os.path.join(BASE_DIR, "..", "candidates.db")
    if not os.path.exists(ROOT_DB):
        print(f"DB not found at {ROOT_DB}")
        return

    conn = sqlite3.connect(ROOT_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Fetch All
    c.execute("SELECT * FROM candidates")
    rows = c.fetchall()
    
    print(f"Re-scoring {len(rows)} candidates...")
    
    updated = 0
    for row in rows:
        try:
            raw_data = json.loads(row['raw_data'])
            
            print(f"Scoring {row['full_name']}...")
            score_data = score_candidate(raw_data, JOB_DESCRIPTION)
            
            experience_breakdown = score_data.get("experience_breakdown", [])
            
            # Update DB
            c.execute('''
                UPDATE candidates 
                SET experience_breakdown = ?, 
                    ai_score = ?,
                    ai_reasoning = ?
                WHERE id = ?
            ''', (
                json.dumps(experience_breakdown),
                score_data.get("score"),
                score_data.get("reasoning"),
                row['id']
            ))
            updated += 1
            
        except Exception as e:
            print(f"Failed to screen {row['id']}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Re-scoring complete. Updated {updated} records.")

if __name__ == "__main__":
    rescore()
