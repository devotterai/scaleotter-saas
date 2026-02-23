import os
import time
import json
import traceback
import subprocess
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Environment constraints
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
DEVICE_ID = os.environ.get("DEVICE_ID")

if not SUPABASE_URL or not SUPABASE_KEY or not DEVICE_ID:
    print("CRITICAL: Missing credentials in .env. Ghost Worker cannot start.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL_INTERVAL_SEC = 5
HEARTBEAT_INTERVAL_SEC = 30
last_heartbeat = 0


def update_heartbeat(status="idle"):
    """Update the devices table so the web app knows this Ghost Laptop is online."""
    global last_heartbeat
    now = time.time()
    if now - last_heartbeat > HEARTBEAT_INTERVAL_SEC:
        try:
            supabase.table("devices").upsert({
                "id": DEVICE_ID,
                "status": status,
                "last_heartbeat": "now()"
            }).execute()
            last_heartbeat = now
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat sent. Status: {status}")
        except Exception as e:
            print(f"Failed to send heartbeat: {e}")


def fail_job(job_id, error_message):
    try:
        supabase.table("job_runs").update({
            "status": "failed",
            "error_message": str(error_message)
        }).eq("id", job_id).execute()
        update_heartbeat("idle")
    except Exception as e:
        print(f"Failed to mark run {job_id} as failed: {e}")


def success_job(job_id, result=None):
    try:
        supabase.table("job_runs").update({
            "status": "completed",
            "result": result or {}
        }).eq("id", job_id).execute()
        update_heartbeat("idle")
    except Exception as e:
        print(f"Failed to mark run {job_id} as completed: {e}")


def execute_job(job):
    job_id = job.get("id")
    job_type = job.get("job_type")
    payload = job.get("payload", {})
    campaign_id = job.get("campaign_id")
    org_id = job.get("organization_id")
    
    print(f"\n--- Starting Job: {job_id} ({job_type}) ---")
    update_heartbeat("running")

    # Mark job as running
    supabase.table("job_runs").update({"status": "running"}).eq("id", job_id).execute()

    try:
        if job_type == "login":
            print("Executing login workflow...")
            import scripts.login
            # Login script handles the 2FA state machine via the Supabase client
            result = scripts.login.run(supabase, DEVICE_ID, job_id, payload)
            success_job(job_id, result)
            
        elif job_type == "connect":
            print(f"Executing connection workflow for campaign: {campaign_id}")
            import scripts.connect
            result = scripts.connect.run(supabase, DEVICE_ID, job_id, campaign_id, org_id)
            success_job(job_id, result)
            
        elif job_type == "message":
            print(f"Executing message workflow for campaign: {campaign_id}")
            import scripts.message
            result = scripts.message.run(supabase, DEVICE_ID, job_id, campaign_id)
            success_job(job_id, result)
            
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

    except Exception as e:
        print("JOB FAILED:")
        traceback.print_exc()
        fail_job(job_id, str(e))
        
    print(f"--- Finished Job: {job_id} ---\n")


def check_for_jobs():
    try:
        response = supabase.table("job_runs") \
            .select("*") \
            .eq("device_id", DEVICE_ID) \
            .eq("status", "pending") \
            .order("created_at") \
            .limit(1) \
            .execute()
            
        jobs = response.data
        if jobs and len(jobs) > 0:
            return jobs[0]
            
    except Exception as e:
        print(f"Error checking jobs: {e}")
    return None


def main_loop():
    print(f"Starting ScaleOtter Ghost Worker. ID: {DEVICE_ID}", flush=True)
    update_heartbeat("idle")
    
    while True:
        try:
            job = check_for_jobs()
            
            if job:
                execute_job(job)
            else:
                update_heartbeat("idle")
                
            time.sleep(POLL_INTERVAL_SEC)
            
        except KeyboardInterrupt:
            print("\nShutting down Ghost Worker...")
            update_heartbeat("offline")
            break
        except Exception as e:
            print(f"Worker loop error: {e}")
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main_loop()
