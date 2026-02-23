import os
import json
from openai import OpenAI

def get_client(api_key):
    if not api_key:
        raise ValueError("Missing OpenAI API Key")
    return OpenAI(api_key=api_key)

def build_pdl_query(user_input, openai_key):
    client = get_client(openai_key)
    system_prompt = """
    You are an expert SQL Generator for the People Data Labs (PDL) API.
    Your goal is to convert Natural Language requirements into a VALID PDL SQL query.
    
    ### PDL SQL Rules:
    1. Table is always `person`.
    2. Fields: 
       - `job_title` (e.g. 'software engineer')
       - `location_name` (e.g. 'austin, tx')
       - `location_country` (e.g. 'united states')
       - `inferred_years_experience` (integer)
       - `skills` (use LIKE op: skills LIKE '%python%')
       - `industry`
    3. Operators: =, !=, <, <=, >, >=, LIKE, AND, OR, IS NOT NULL.
    4. Strings must be single-quoted.
    5. Be concise. Return ONLY the SQL string. No markdown.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0
        )
        sql = response.choices[0].message.content.strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return None

def score_candidate(candidate_data, job_description, openai_key):
    client = get_client(openai_key)
    system_prompt = """
    You are an Expert AI Recruiter. 
    You will evaluate a candidate profile against a Job Requirement.
    
    ### Output Format (JSON):
    {
        "score": 85,
        "reasoning": "Strong match for tenure (8 yrs) and title.",
        "pros": ["10 years experience", "Ex-Google"],
        "cons": ["No React Native"],
        "experience_breakdown": [
            {"role": "Accounting", "years": 5},
            {"role": "Software Engineering", "years": 6}
        ]
    }
    """
    
    user_prompt = f"""
    ### Job Description:
    {job_description}
    
    ### Candidate Profile:
    Title: {candidate_data.get('headline')}
    Experience: {candidate_data.get('years_experience')} years
    Skills: {', '.join(candidate_data.get('skills', [])[:20])}
    Work History: {json.dumps(candidate_data.get('work_history', []))}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error scoring candidate: {e}")
        return {"score": 0, "reasoning": "AI Scoring Failed", "pros": [], "cons": [], "experience_breakdown": []}

def generate_connection_note(candidate_data, openai_key):
    client = get_client(openai_key)
    system_prompt = """
    You are a skilled recruiter writing LinkedIn connection request notes.
    Keep it under 280 characters.
    Return ONLY the note text.
    """
    
    name = candidate_data.get("full_name", "there")
    first_name = name.split()[0] if name else "there"
    
    user_prompt = f"""
    Generate connection note for: {first_name}
    Current Role: {candidate_data.get('headline')}
    Company: {candidate_data.get('company')}
    Summary: {candidate_data.get('summary')}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )
        note = response.choices[0].message.content.strip()
        if len(note) > 295:
            note = note[:292] + "..."
        return note
    except Exception as e:
        print(f"Error generating connection note: {e}")
        return None

def generate_initial_message(candidate_data, job_context, openai_key):
    client = get_client(openai_key)
    job_title = job_context.get("job_title", "the role")
    company = job_context.get("company", "our company")
    tone = job_context.get("tone", "professional")

    system_prompt = f"""
    You are a skilled recruiter writing a LinkedIn direct message to someone who just accepted your connection request.
    Role: {job_title}
    Company: {company}
    Tone: {tone}
    Write EXACTLY 2-3 sentences. Return ONLY the message text.
    """
    
    name = candidate_data.get("full_name", "there")
    first_name = name.split()[0] if name else "there"
    
    user_prompt = f"""
    Generate a follow-up message for: {first_name}
    Current Role: {candidate_data.get('headline')}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=120
        )
        msg = response.choices[0].message.content.strip()
        if msg.startswith('"') and msg.endswith('"'):
            msg = msg[1:-1]
        return msg
    except Exception as e:
        print(f"Error generating initial message: {e}")
        return None
