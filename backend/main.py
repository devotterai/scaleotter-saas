import os
import sys
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Add local directory to path for direct imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.sourcing_orchestrator import source_and_score_candidates
from llm_helper import generate_connection_note, generate_initial_message

app = FastAPI(title="ScaleOtter AI Logic Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase Admin Client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Warning: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in backend scope.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_org_api_keys(org_id: str):
    """Retrieve API keys for the organization securely."""
    try:
        response = supabase.table("organizations").select("openai_api_key, pdl_api_key").eq("id", org_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        openai_key = response.data.get("openai_api_key")
        pdl_key = response.data.get("pdl_api_key")
        
        if not openai_key or not pdl_key:
            raise HTTPException(status_code=400, detail="Organization is missing OpenAI or PDL API Keys. Please configure them in Settings.")
            
        return openai_key, pdl_key
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ScaleOtter SaaS Backend is running"}


class SourceRequest(BaseModel):
    query: str
    limit: int = 10
    organization_id: str
    campaign_id: str

@app.post("/api/source")
async def source_candidates(request: SourceRequest):
    """
    Triggers AI Sourcing (PDL -> AI Scoring).
    Saves candidates directly to Supabase.
    """
    openai_key, pdl_key = get_org_api_keys(request.organization_id)
    
    try:
        result = await source_and_score_candidates(
            user_query=request.query, 
            pdl_key=pdl_key, 
            openai_key=openai_key, 
            limit=request.limit
        )
        if "error" in result:
             raise HTTPException(status_code=500, detail=str(result))
             
        # Auto-save candidates to Supabase
        saved_count = 0
        for c in result.get("candidates", []):
            candidate_payload = {
                "id": c.get("id"),
                "campaign_id": request.campaign_id,
                "organization_id": request.organization_id,
                "name": c.get("full_name"),
                "linkedin_url": c.get("linkedin_url"),
                "campaign_status": "pending",
                "message_status": "draft",
                "data": c  # Store the full enriched json block
            }
            try:
                supabase.table("candidates").insert(candidate_payload).execute()
                saved_count += 1
            except Exception as e:
                print(f"Failed to save candidate {c.get('id')}: {e}")
                
        return {"status": "success", "sourced": len(result.get("candidates", [])), "saved": saved_count}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Sourcing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GenerateNotesRequest(BaseModel):
    organization_id: str

@app.post("/api/campaigns/{campaign_id}/generate-notes")
async def generate_notes(campaign_id: str, request: GenerateNotesRequest):
    """Generate AI connection notes for all pending candidates that don't have one yet."""
    openai_key, _ = get_org_api_keys(request.organization_id)
    
    # Fetch candidates from Supabase
    try:
        response = supabase.table("candidates").select("*").eq("campaign_id", campaign_id).eq("campaign_status", "pending").execute()
        candidates = response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
        
    pending = [c for c in candidates if not c.get("connection_note")]
    
    if not pending:
        return {"status": "success", "generated": 0, "message": "All candidates already have notes."}
    
    generated = 0
    for cand in pending:
        try:
            cad_data = cand.get("data", {})
            note = generate_connection_note(cad_data, openai_key)
            if note:
                supabase.table("candidates").update({"connection_note": note, "updated_at": "now()"}).eq("id", cand["id"]).execute()
                generated += 1
        except Exception as e:
            print(f"Note generation error for {cand.get('name')}: {e}")
    
    return {"status": "success", "generated": generated, "message": f"Generated {generated} notes."}


class GenerateMessagesRequest(BaseModel):
    organization_id: str

@app.post("/api/campaigns/{campaign_id}/generate-messages")
async def generate_messages(campaign_id: str, request: GenerateMessagesRequest):
    """Generate AI personalized messages for all connection_sent candidates."""
    openai_key, _ = get_org_api_keys(request.organization_id)
    
    # Fetch campaign context
    try:
        camp_resp = supabase.table("campaigns").select("job_context").eq("id", campaign_id).single().execute()
        job_context = camp_resp.data.get("job_context", {})
        if not job_context:
            raise HTTPException(status_code=400, detail="Campaign has no job context.")
            
        cand_resp = supabase.table("candidates").select("*").eq("campaign_id", campaign_id).eq("campaign_status", "connection_sent").execute()
        candidates = cand_resp.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    to_generate = [c for c in candidates if not c.get("initial_message")]
    
    generated = 0
    errors = 0
    for c in to_generate:
        try:
            cand_data = c.get("data", {})
            message = generate_initial_message(cand_data, job_context, openai_key)
            if message:
                supabase.table("candidates").update({"initial_message": message, "message_status": "draft", "updated_at": "now()"}).eq("id", c["id"]).execute()
                generated += 1
            else:
                errors += 1
        except Exception as e:
            print(f"Error generating message for {c.get('name')}: {e}")
            errors += 1
    
    return {
        "status": "success",
        "generated": generated,
        "errors": errors,
        "already_had_messages": len(candidates) - len(to_generate)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
