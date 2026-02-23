
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

PDL_KEY = os.getenv("PDL_API_KEY")
if not PDL_KEY:
    print("Error: PDL_API_KEY not found in .env")
    exit(1)

url = "https://api.peopledatalabs.com/v5/person/search"

# SQL Query - stricter check
sql_query = "SELECT * FROM person WHERE job_title='software engineer' AND location_country='united states' AND inferred_years_experience > 50"

headers = {
    "X-Api-Key": PDL_KEY,
    "Content-Type": "application/json"
}

payload = {
    "sql": sql_query,
    "size": 1,
    "pretty": True
}

try:
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total Matches for > 50 years: {data.get('total', 'Unknown')}")
        if data.get('data'):
            person = data['data'][0]
            # Print ALL keys to find the right one
            print("\n--- Person Keys ---")
            print(json.dumps(person, indent=2))
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Exception: {e}")
