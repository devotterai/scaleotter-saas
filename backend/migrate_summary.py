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
    
    # Add Column (ignore if exists)
    try:
        c.execute("ALTER TABLE candidates ADD COLUMN summary TEXT")
        print("Added column 'summary'.")
    except sqlite3.OperationalError:
        print("Column 'summary' already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
