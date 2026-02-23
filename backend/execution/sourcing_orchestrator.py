import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.source_candidate_api import search_candidates_pdl
from execution.experience_logic import calculate_relevant_experience
from llm_helper import build_pdl_query, score_candidate

async def source_and_score_candidates(user_query, pdl_key, openai_key, job_description=None, limit=10):
    """
    Orchestrates the full sourcing flow:
    1. NL -> SQL
    2. SQL -> PDL Candidates
    3. Candidates -> AI Scoring
    """
    print(f"Generating SQL for: {user_query}")
    sql_query = build_pdl_query(user_query, openai_key)
    if not sql_query:
        return {"error": "Failed to generate SQL query"}
    
    print(f"SQL: {sql_query}")
    
    print("Searching PDL...")
    result = search_candidates_pdl(sql_query, pdl_key, size=limit)
    if "error" in result:
        return result
        
    candidates = result.get("candidates", [])
    print(f"Found {len(candidates)} candidates. Scoring...")
    
    jd = job_description or user_query
    
    scored_candidates = []
    for cand in candidates:
        try:
            score_data = score_candidate(cand, jd, openai_key)
            cand["ai_score"] = score_data.get("score", 0)
            cand["ai_reasoning"] = score_data.get("reasoning", "")
            cand["ai_pros"] = score_data.get("pros", [])
            cand["ai_cons"] = score_data.get("cons", [])
            cand["experience_breakdown"] = score_data.get("experience_breakdown", [])
             
            cand["relevant_experience"] = calculate_relevant_experience(cand.get("work_history", []), user_query)
             
        except Exception as e:
             print(f"Scoring error: {e}")
             cand["ai_score"] = 0
             cand["relevant_experience"] = 0
             
        scored_candidates.append(cand)
        
    scored_candidates.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    
    return {
        "sql_generated": sql_query,
        "total_matches": result.get("total_matches"),
        "candidates": scored_candidates
    }
