import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidates.db")

def get_dynamic_daily_limit(default_max=30, start_limit=5, increment=2):
    """
    Calculates the daily limit based on account warm-up status.
    Rule: Start at 5. If yesterday's usage was near the limit, increase by 2.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get all dates with activity
        c.execute("SELECT DISTINCT substr(updated_at, 1, 10) FROM campaign_candidates WHERE status='connection_sent' ORDER BY 1 DESC")
        active_days = [row[0] for row in c.fetchall()]
        conn.close()

        if not active_days:
            return start_limit
        
        # Simple Logic: 
        # Base limit = start_limit + (total_active_days * increment)
        # Cap at default_max
        
        # More robust logic: 
        # Check strict consecutive days? No, that's too punishing for a user who skips a weekend.
        # Let's just use 'total active days' as a proxy for trust.
        
        calculated = start_limit + (len(active_days) * increment)
        
        final_limit = min(calculated, default_max)
        
        # print(f"DEBUG: Warmup Calculation: {len(active_days)} active days. Limit: {final_limit}")
        return final_limit

    except Exception as e:
        print(f"Error calculating dynamic limit: {e}")
        return 10  # Safe fallback
