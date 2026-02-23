import sys
import os
import json
import sqlite3

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from database import add_manual_candidate

# User provided JSON
raw_json = """
[
  {
    "basic_info": {
      "fullname": "Jarod Walker",
      "first_name": "Jarod",
      "last_name": "Walker",
      "headline": "Financial Analyst II at Truist Investment Services, Inc. | Truist Wealth",
      "public_identifier": "jarodwalker",
      "profile_url": "https://linkedin.com/in/jarodwalker",
      "profile_picture_url": "https://media.licdn.com/dms/image/v2/D5603AQEBuF8F0V8diw/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1680117204486?e=1772668800&v=beta&t=9WI_LBHCw6ewk8K30eIOHjZvaILx7xi-7NUuL8vDKu4",
      "about": "Serving our clients by providing financial education and guidance to help you in pursuit of your financial goals",
      "location": {
        "country": "United States",
        "city": "Charlotte, North Carolina",
        "full": "Charlotte, North Carolina, United States",
        "country_code": "US"
      },
      "creator_hashtags": [],
      "is_creator": false,
      "is_influencer": false,
      "is_premium": false,
      "open_to_work": false,
      "created_timestamp": 1631026820434,
      "show_follower_count": false,
      "background_picture_url": "https://media.licdn.com/dms/image/v2/D4E16AQGK4zG82UBPCw/profile-displaybackgroundimage-shrink_350_1400/profile-displaybackgroundimage-shrink_350_1400/0/1707930892802?e=1772668800&v=beta&t=4mqQVbAw8VIXENhyOK2jYX_4dTLhWkmrubs6mC7KQrI",
      "urn": "ACoAADeD-K0BisRPphH2qxGcBwaX8okBdBSJ4qs",
      "follower_count": 498,
      "connection_count": 497,
      "current_company": "Truist Investment Services, Inc., Truist Wealth",
      "current_company_urn": "",
      "top_skills": [],
      "email": null
    },
    "experience": [
      {
        "title": "Financial Analyst II",
        "company": "Truist Investment Services, Inc., Truist Wealth",
        "location": "Charlotte, North Carolina",
        "description": "Due to industry regulations, I am unable to accept recommendations and endorsements. TIS will not accept purchase or sale orders via LinkedIn or its messaging system. Truist Investment Services, Inc., member FINRA/SIPC, is a wholly owned non-bank subsidiary of Truist Financial Corporation. Securities and insurance products or annuities sold, offered or recommended by Truist Investment Services are not a deposit, not FDIC insured, not guaranteed by a bank, not insured by any federal government agency and may lose value. Not all products and services are available in all states and financial advisors for Truist Investment Services may only conduct business in states and jurisdictions where they are properly registered. Therefore, a response for information may be delayed. Investors outside of the United States are subject to additional securities and tax regulations within their applicable jurisdictions that are not addressed on this site. For more information please contact your financial advisor. For additional important disclosures, please visit: https://www.truist.com/wealth/tis-disclosure",
        "duration": "May 2025 - Present · 10 mos",
        "start_date": {
          "year": 2025,
          "month": "May"
        },
        "is_current": true,
        "company_linkedin_url": "https://www.linkedin.com/search/results/all/?keywords=Truist+Investment+Services%2C+Inc%2E%2C+Truist+Wealth"
      },
      {
        "title": "Registered Client Service Associate at Truist Investment Services, Inc.",
        "company": "Truist Wealth",
        "location": "Charlotte, North Carolina, United States",
        "description": "Due to industry regulations, I am unable to accept recommendations and endorsements. TIS will not accept purchase or sale orders via LinkedIn or its messaging system. Truist Investment Services, Inc., member FINRA/SIPC, is a wholly owned non-bank subsidiary of Truist Financial Corporation. Securities and insurance products or annuities sold, offered or recommended by Truist Investment Services are not a deposit, not FDIC insured, not guaranteed by a bank, not insured by any federal government agency and may lose value. Not all products and services are available in all states and financial advisors for Truist Investment Services may only conduct business in states and jurisdictions where they are properly registered. Therefore, a response for information may be delayed. Investors outside of the United States are subject to additional securities and tax regulations within their applicable jurisdictions that are not addressed on this site. For more information please contact your financial advisor. For additional important disclosures, please visit: https://www.truist.com/wealth/tis-disclosure",
        "duration": "Feb 2024 - May 2025 · 1 yr 4 mos",
        "start_date": {
          "year": 2024,
          "month": "Feb"
        },
        "end_date": {
          "year": 2025,
          "month": "May"
        },
        "is_current": false,
        "company_linkedin_url": "https://www.linkedin.com/company/69680824/",
        "company_logo_url": "https://media.licdn.com/dms/image/v2/C4D0BAQGWCu3SAApXKA/company-logo_400_400/company-logo_400_400/0/1630537673542/truist_wealth_logo?e=1772668800&v=beta&t=WfvitHKQx5GBTyDvjRvjHcjsOz0f_Yt3q3srtBrod44",
        "employment_type": "Full-time",
        "location_type": "On-site",
        "company_id": "69680824"
      },
      {
        "title": "Financial Planner",
        "company": "MassMutual Carolinas",
        "location": "Charlotte, North Carolina, United States",
        "duration": "Mar 2023 - Feb 2024 · 1 yr",
        "start_date": {
          "year": 2023,
          "month": "Mar"
        },
        "end_date": {
          "year": 2024,
          "month": "Feb"
        },
        "is_current": false,
        "company_linkedin_url": "https://www.linkedin.com/company/964088/",
        "company_logo_url": "https://media.licdn.com/dms/image/v2/C560BAQGk_W_ujxXQoQ/company-logo_400_400/company-logo_400_400/0/1631399174337/massmutualcarolinas_logo?e=1772668800&v=beta&t=A-b_sQ9E2XQ3KvVhNH4baRGj55gVM68XTXs2u3asv4c",
        "employment_type": "Contract",
        "location_type": "On-site",
        "company_id": "964088"
      },
      {
        "title": "Financial Planner",
        "company": "The Pelora Group",
        "location": "Charlotte, North Carolina, United States",
        "duration": "Mar 2023 - Feb 2024 · 1 yr",
        "start_date": {
          "year": 2023,
          "month": "Mar"
        },
        "end_date": {
          "year": 2024,
          "month": "Feb"
        },
        "is_current": false,
        "company_linkedin_url": "https://www.linkedin.com/company/81550136/",
        "company_logo_url": "https://media.licdn.com/dms/image/v2/C560BAQHQhts80fgJ4w/company-logo_400_400/company-logo_400_400/0/1652815171232?e=1772668800&v=beta&t=TmVfhC6M5OGzHuNsXdul-2cSw9o8xvTnpRRD2CEORiQ",
        "employment_type": "Contract",
        "location_type": "On-site",
        "company_id": "81550136"
      }
    ],
    "education": [
      {
        "school": "University of North Carolina at Charlotte",
        "degree": "Bachelor's degree, Finance, General",
        "degree_name": "Bachelor's degree",
        "field_of_study": "Finance, General",
        "duration": "Aug 2020 - Dec 2022",
        "school_linkedin_url": "https://www.linkedin.com/company/166586/",
        "school_logo_url": "https://media.licdn.com/dms/image/v2/D560BAQFungcgjUTABw/company-logo_400_400/B56ZeEs4dcGoAY-/0/1750278048123/unc_charlotte_logo?e=1772668800&v=beta&t=pHCwrzVqzyCZ0KwmQMvY9KVec2J2tJQMjbMl2-9MezM",
        "start_date": {
          "year": 2020,
          "month": "Aug"
        },
        "end_date": {
          "year": 2022,
          "month": "Dec"
        },
        "school_id": "166586"
      }
    ],
    "certifications": [
      {
        "name": "Insurance Agent, Accident, Health, Life, Variable Life & Variable Annuities",
        "issuer": "National Association of Insurance Commissioners (NAIC)",
        "issued_date": "Issued Jan 2023 · Expired Jan 2025"
      },
      {
        "name": "Series 7",
        "issuer": "FINRA",
        "issued_date": "Issued Aug 2023"
      }
    ]
  }
]
"""

def main():
    data = json.loads(raw_json)
    profile = data[0]
    
    basic = profile["basic_info"]
    fullname = basic["fullname"]
    url = basic["profile_url"]
    
    # Prepare rich data dict
    profile_data = {
        "headline": basic.get("headline", ""),
        "company": basic.get("current_company", ""),
        "location": basic.get("location", {}).get("full", ""),
        "summary": basic.get("about", ""),
        "raw_data": profile
    }
    
    # Campaign ID for 'new'
    campaign_id = "91ee088d-4096-4cb4-96fa-12daaaabcdf9"
    
    print(f"Adding {fullname} to campaign {campaign_id}...")
    success, cid = add_manual_candidate(campaign_id, fullname, url, profile_data)
    
    if success:
        print(f"Success! Candidate ID: {cid}")
    else:
        print("Failed to add candidate.")

if __name__ == "__main__":
    main()
