from datetime import datetime

def parse_date(date_str):
    """Parses 'YYYY-MM' or 'YYYY' into a datetime object."""
    if not date_str:
        return datetime.now()
    if date_str.lower() == "present":
        return datetime.now()
    
    try:
        if len(date_str) == 4:
            return datetime.strptime(date_str, "%Y")
        return datetime.strptime(date_str, "%Y-%m")
    except:
        return datetime.now()

def calculate_relevant_experience(work_history, query):
    """
    Calculates years of experience in roles matching the query.
    """
    if not work_history:
        return 0.0
        
    relevant_years = 0.0
    query_terms = query.lower().split()
    # Filter out common stop words if necessary, but simple split is fine for MVP
    
    for role in work_history:
        title = role.get("title", "").lower()
        if not title:
            continue
            
        # Check if ANY significant term from query is in title
        # e.g. "Software Engineer" -> matches "Senior Software Engineer"
        # "Marketing Manager" -> matches "Product Marketing Manager"
        is_relevant = False
        for term in query_terms:
            if len(term) > 2 and term in title: # Avoid matching "in", "at", "of"
                is_relevant = True
                break
        
        if is_relevant:
            start = parse_date(role.get("start_date") or role.get("start"))
            end = parse_date(role.get("end_date") or role.get("end"))
            
            # Calculate duration in years
            diff = (end - start).days / 365.0
            if diff > 0:
                relevant_years += diff
                
    return round(relevant_years, 1)
