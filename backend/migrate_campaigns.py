import sqlite3
import os

# Use absolute path to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "candidates.db")

def migrate():
    # Connect to root DB 
    ROOT_DB = os.path.join(BASE_DIR, "..", "candidates.db")
    if not os.path.exists(ROOT_DB):
        print(f"DB not found at {ROOT_DB}")
        return

    conn = sqlite3.connect(ROOT_DB)
    c = conn.cursor()
    
    # 1. Campaigns Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active', -- active, paused, completed
            created_at TIMESTAMP
        )
    ''')
    print("Ensured 'campaigns' table exists.")

    # 2. Campaign Candidates Table (Join Table)
    c.execute('''
        CREATE TABLE IF NOT EXISTS campaign_candidates (
            campaign_id TEXT,
            candidate_id TEXT,
            status TEXT DEFAULT 'pending', -- pending, connection_sent, accepted, replied
            updated_at TIMESTAMP,
            PRIMARY KEY (campaign_id, candidate_id),
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id),
            FOREIGN KEY(candidate_id) REFERENCES candidates(id)
        )
    ''')
    print("Ensured 'campaign_candidates' table exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
