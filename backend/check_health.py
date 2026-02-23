import requests
try:
    r = requests.get("http://127.0.0.1:8000/health")
    print(r.status_code)
    print(r.json())
except Exception as e:
    print(e)
