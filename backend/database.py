import sqlite3
import json
from datetime import datetime
import os
import uuid

# Use absolute path to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "..", "candidates.db")

def init_db():
    """Initialize the candidates database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            full_name TEXT,
            headline TEXT,
            company TEXT,
            location TEXT,
            linkedin_url TEXT,
            years_experience REAL,
            ai_score INTEGER,
            ai_reasoning TEXT,
            relevant_experience REAL,
            experience_breakdown TEXT,
            summary TEXT,
            education TEXT,
            skills TEXT,
            work_email TEXT,
            raw_data TEXT,
            created_at TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            send_notes INTEGER DEFAULT 0,
            job_context TEXT,
            created_at TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS campaign_candidates (
            campaign_id TEXT,
            candidate_id TEXT,
            status TEXT DEFAULT 'pending',
            connection_note TEXT,
            initial_message TEXT,
            message_status TEXT,
            updated_at TIMESTAMP,
            PRIMARY KEY (campaign_id, candidate_id)
        )
    ''')

    # Migrations for existing DBs
    migrations = [
        "ALTER TABLE campaigns ADD COLUMN send_notes INTEGER DEFAULT 0",
        "ALTER TABLE campaigns ADD COLUMN job_context TEXT",
        "ALTER TABLE campaign_candidates ADD COLUMN connection_note TEXT",
        "ALTER TABLE campaign_candidates ADD COLUMN initial_message TEXT",
        "ALTER TABLE campaign_candidates ADD COLUMN message_status TEXT",
    ]
    for sql in migrations:
        try:
            c.execute(sql)
        except Exception:
            pass  # Column already exists

    conn.commit()
    conn.close()

def save_candidate(candidate):
    """Save or update a candidate in the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Extract company from work_history if top-level is missing
        company = candidate.get("company")
        if not company:
             work_history = candidate.get("work_history", [])
             if work_history and isinstance(work_history, list) and len(work_history) > 0:
                 company = work_history[0].get("company")

        c.execute('''
            INSERT OR REPLACE INTO candidates (
                id, full_name, headline, company, location, 
                linkedin_url, years_experience, ai_score, ai_reasoning, 
                relevant_experience, experience_breakdown, summary,
                raw_data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            candidate.get("id"),
            candidate.get("full_name"),
            candidate.get("headline"),
            company or "Unknown",
            candidate.get("location"),
            candidate.get("linkedin_url"),
            candidate.get("years_experience"),
            candidate.get("ai_score"),
            candidate.get("ai_reasoning"),
            candidate.get("relevant_experience", 0),
            json.dumps(candidate.get("experience_breakdown", [])),
            candidate.get("summary"),
            json.dumps(candidate),
            datetime.now()
        ))
        conn.commit()
        print(f"Saved candidate: {candidate.get('full_name')}")
    except Exception as e:
        print(f"DB Save Error: {e}")
    finally:
        conn.close()

def get_all_candidates():
    """Retrieve all saved candidates."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM candidates ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        results = []
        for row in rows:
            cand = dict(row)
            # Parse breakdown if exists
            if cand.get("experience_breakdown"):
                try:
                    cand["experience_breakdown"] = json.loads(cand["experience_breakdown"])
                except:
                    cand["experience_breakdown"] = []
            else:
                cand["experience_breakdown"] = []

            # Extract rich data from raw_data
            try:
                raw = json.loads(cand.get("raw_data", "{}"))
                cand["education"] = raw.get("education", [])
                cand["skills"] = raw.get("skills", [])
                if not cand.get("summary"): # Use column if exists, else raw
                    cand["summary"] = raw.get("summary")
            except:
                cand["education"] = []
                cand["skills"] = []

            results.append(cand)
            
        print(f"Retrieved {len(results)} candidates from DB")
        return results
    except Exception as e:
        print(f"DB Get Error: {e}")
        return []

# --- Campaign Functions ---

def create_campaign(name, send_notes=False, job_context=None):
    """Create a new campaign."""
    import uuid
    campaign_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        job_ctx_json = json.dumps(job_context) if job_context else None
        c.execute("INSERT INTO campaigns (id, name, send_notes, job_context, created_at) VALUES (?, ?, ?, ?, ?)", 
                  (campaign_id, name, 1 if send_notes else 0, job_ctx_json, datetime.now()))
        conn.commit()
        return {"id": campaign_id, "name": name, "send_notes": send_notes, "job_context": job_context, "status": "active"}
    except Exception as e:
        print(f"Create Campaign Error: {e}")
        return None
    finally:
        conn.close()

def get_campaigns():
    """Get all campaigns with member counts."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        # Get campaigns with count of members
        c.execute('''
            SELECT c.*, count(cc.candidate_id) as member_count 
            FROM campaigns c 
            LEFT JOIN campaign_candidates cc ON c.id = cc.campaign_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        ''')
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Get Campaigns Error: {e}")
        return []
    finally:
        conn.close()

def get_campaign_by_id(campaign_id):
    """Get a single campaign by ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Get Campaign By ID Error: {e}")
        return None
    finally:
        conn.close()

def add_candidate_to_campaign(campaign_id, candidate_id):
    """Add a candidate to a campaign."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR IGNORE INTO campaign_candidates (campaign_id, candidate_id, status, connection_note, updated_at)
            VALUES (?, ?, 'pending', NULL, ?)
        ''', (campaign_id, candidate_id, datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        print(f"Add Member Error: {e}")
        return False
    finally:
        conn.close()

def add_manual_candidate(campaign_id, name, linkedin_url, profile_data=None):
    """
    Manually add a candidate to a campaign for testing.
    profile_data: Optional dict with keys: headline, company, location, summary, raw_data (dict)
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Check if candidate exists by URL
        c.execute("SELECT id FROM candidates WHERE linkedin_url = ?", (linkedin_url,))
        row = c.fetchone()
        
        if row:
            candidate_id = row[0]
            # Optionally update existing candidate with new data if provided? 
            # For now, let's just use existing to avoid overwriting scrapes.
        else:
            # Create new candidate
            candidate_id = str(uuid.uuid4())
            
            p = profile_data or {}
            headline = p.get("headline", "")
            company = p.get("company", "")
            location = p.get("location", "")
            summary = p.get("summary", "")
            raw_blob = json.dumps(p.get("raw_data", {}))
            
            c.execute('''
                INSERT INTO candidates (id, full_name, linkedin_url, headline, company, location, summary, created_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (candidate_id, name, linkedin_url, headline, company, location, summary, datetime.now(), raw_blob))
        
        # Add to campaign
        c.execute('''
            INSERT OR IGNORE INTO campaign_candidates (campaign_id, candidate_id, status, connection_note, updated_at)
            VALUES (?, ?, 'pending', NULL, ?)
        ''', (campaign_id, candidate_id, datetime.now()))
        
        conn.commit()
        return True, candidate_id
    except Exception as e:
        print(f"Add Manual Candidate Error: {e}")
        return False, None
    finally:
        conn.close()

def delete_candidate_from_campaign(campaign_id, candidate_id):
    """Remove a candidate from a campaign."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM campaign_candidates WHERE campaign_id = ? AND candidate_id = ?", (campaign_id, candidate_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Candidate Error: {e}")
        return False
    finally:
        conn.close()

def get_campaign_details(campaign_id):
    """Get candidates in a campaign."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('''
            SELECT cand.*, cc.status as campaign_status, cc.connection_note, cc.updated_at as status_updated_at
            FROM candidates cand
            JOIN campaign_candidates cc ON cand.id = cc.candidate_id
            WHERE cc.campaign_id = ?
        ''', (campaign_id,))
        
        rows = c.fetchall()
        results = []
        for row in rows:
            cand = dict(row)
            # Parse rich data
            try:
                raw = json.loads(cand.get("raw_data", "{}"))
                cand["education"] = raw.get("education", [])
                cand["skills"] = raw.get("skills", [])
                if not cand.get("summary"):
                     cand["summary"] = raw.get("summary")
            except:
                pass
            results.append(cand)
            
        return results
    except Exception as e:
        print(f"Get Campaign Details Error: {e}")
        return []
    finally:
        conn.close()

def update_campaign_status(campaign_id, candidate_id, status):
    """Update the status of a candidate in a campaign."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE campaign_candidates
            SET status = ?, updated_at = ?
            WHERE campaign_id = ? AND candidate_id = ?
        ''', (status, datetime.now(), campaign_id, candidate_id))
        conn.commit()
    except Exception as e:
        print(f"Update Campaign Status Error: {e}")
    finally:
        conn.close()

def update_candidate_message(campaign_id, candidate_id, message, status="draft"):
    """Update the initial message and its status for a candidate in a campaign."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE campaign_candidates
            SET initial_message = ?, message_status = ?, updated_at = ?
            WHERE campaign_id = ? AND candidate_id = ?
        ''', (message, status, datetime.now(), campaign_id, candidate_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Candidate Message Error: {e}")
        return False
    finally:
        conn.close()

def update_connection_note(campaign_id, candidate_id, note):
    """Update the connection note for a candidate in a campaign."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE campaign_candidates
            SET connection_note = ?, updated_at = ?
            WHERE campaign_id = ? AND candidate_id = ?
        ''', (note, datetime.now(), campaign_id, candidate_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Connection Note Error: {e}")
        return False
    finally:
        conn.close()

def get_candidates_for_messaging(campaign_id):
    """Get connection_sent candidates with their message data for the review UI."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('''
            SELECT cand.id, cand.full_name, cand.headline, cand.company, cand.linkedin_url,
                   cand.summary, cand.years_experience, cand.ai_score, cand.ai_reasoning,
                   cand.raw_data,
                   cc.status as campaign_status, cc.initial_message, cc.message_status
            FROM candidates cand
            JOIN campaign_candidates cc ON cand.id = cc.candidate_id
            WHERE cc.campaign_id = ?
            AND cc.status IN ('connection_sent', 'message_sent', 'accepted', 'declined')
        ''', (campaign_id,))
        
        results = []
        for row in c.fetchall():
            cand = dict(row)
            try:
                raw = json.loads(cand.get("raw_data", "{}"))
                cand["education"] = raw.get("education", [])
                cand["skills"] = raw.get("skills", []) if not cand.get("skills") else cand["skills"]
            except:
                pass
            if "raw_data" in cand:
                del cand["raw_data"]  # Don't send raw blob to frontend
            results.append(cand)
        
        return results
    except Exception as e:
        print(f"Get Candidates For Messaging Error: {e}")
        return []
    finally:
        conn.close()
