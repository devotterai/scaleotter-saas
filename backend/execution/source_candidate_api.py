
import os
import requests
import json
from datetime import datetime

def calculate_experience_years(experience_data):
    """
    Manually calculates total years of experience from the experience array.
    Sum of durations of all roles.
    """
    if not experience_data:
        return 0
        
    total_months = 0
    # Simple deduplication or overlap logic could be added here, 
    # but for now we sum ranges. PDL usually sorts them.
    # A better approach is to merge overlapping ranges.
    
    ranges = []
    
    for job in experience_data:
        start = job.get('start_date')
        end = job.get('end_date')
        
        if not start:
            continue
            
        # Parse dates (PDL uses YYYY-MM or YYYY-MM-DD or YYYY)
        try:
            start_date = _parse_pdl_date(start)
            end_date = _parse_pdl_date(end) if end else datetime.now()
            
            if start_date and end_date:
                ranges.append((start_date, end_date))
        except:
            continue
            
    # Merge ranges to handle overlaps (person working 2 jobs at once shouldn't count double)
    merged_ranges = _merge_date_ranges(ranges)
    
    for start, end in merged_ranges:
        delta = end - start
        total_months += delta.days / 30.44
        
    return round(total_months / 12.0, 1)

def _parse_pdl_date(date_str):
    try:
        if len(date_str) == 4: # YYYY
            return datetime(int(date_str), 1, 1)
        if len(date_str) == 7: # YYYY-MM
            return datetime(int(date_str[:4]), int(date_str[5:7]), 1)
        return datetime.fromisoformat(date_str)
    except:
        return None

def _merge_date_ranges(ranges):
    """
    Merges overlapping date ranges.
    input: [(start1, end1), (start2, end2)]
    """
    if not ranges:
        return []
        
    # Sort by start date
    ranges.sort(key=lambda x: x[0])
    
    merged = []
    current_start, current_end = ranges[0]
    
    for next_start, next_end in ranges[1:]:
        if next_start <= current_end: # Overlap
            current_end = max(current_end, next_end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = next_start, next_end
            
    merged.append((current_start, current_end))
    return merged

def _safe_get_list_first(data, key):
    val = data.get(key)
    if isinstance(val, list) and len(val) > 0:
        return val[0]
    return None

def search_candidates_pdl(sql_query, pdl_key, size=10):
    """
    Executes a SQL query against PDL and returns normalized candidates.
    """
    if not pdl_key:
        return {"error": "Missing PDL_API_KEY"}

    headers = {
        "X-Api-Key": pdl_key,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip" 
    }

    payload = {
        "sql": sql_query,
        "size": size,
        "pretty": False
    }

    try:
        response = requests.post("https://api.peopledatalabs.com/v5/person/search", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        candidates = []
        for person in data.get('data', []):
            # Normalize Candidate
            exp_years = calculate_experience_years(person.get('experience', []))
            
            candidate = {
                "id": person.get("id"),
                "full_name": person.get("full_name"),
                "headline": person.get("job_title"),
                "location": person.get("location", {}).get("name") if isinstance(person.get("location"), dict) else str(person.get("location")),
                "linkedin_url": person.get("linkedin_url"),
                "years_experience": exp_years,
                "skills": person.get("skills", []) if isinstance(person.get("skills"), list) else [],
                "work_history": _format_work_history(person.get("experience", [])),
                "education": _format_education(person.get("education", [])),
                "education": _format_education(person.get("education", [])),
                "personal_email": _safe_get_list_first(person, "personal_emails"),
                "work_email": person.get("work_email"),
                "summary": person.get("summary")
            }
            candidates.append(candidate)
            
        return {"candidates": candidates, "total_matches": data.get("total", 0)}

    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP Error: {e}", "details": response.text}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return {"error": f"General Error: {e}", "traceback": tb}

def _format_work_history(experience):
    """Simplify generic experience data for UI"""
    history = []
    for job in experience[:5]: # Top 5 only
        if not job:
            continue
        history.append({
            "title": job.get("title", {}).get("name") if isinstance(job.get("title"), dict) else "Unknown",
            "company": job.get("company", {}).get("name") if isinstance(job.get("company"), dict) else "Unknown",
            "start": job.get("start_date"),
            "end": job.get("end_date") or "Present"
        })
    return history

def _format_education(education):
    """Simplify education data"""
    # Defensive check if education is bool or not list
    if not isinstance(education, list):
        return []
        
    edu_list = []
    for edu in education[:2]:
         edu_list.append({
             "school": edu.get("school", {}).get("name") if isinstance(edu.get("school"), dict) else "Unknown",
             "degree": _safe_get_list_first(edu, "degrees")
         })
    return edu_list

if __name__ == "__main__":
    # Test
    query = "SELECT * FROM person WHERE job_title='software engineer' AND location_country='united states' AND inferred_years_experience >= 5"
    result = search_candidates_pdl(query, size=2)
    print(json.dumps(result, indent=2))
