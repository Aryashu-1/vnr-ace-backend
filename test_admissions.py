import requests, json, sys
url = 'http://127.0.0.1:8000/admissions/chat'
payload = {'message': 'What are the eligibility criteria for CSE?'}
try:
    r = requests.post(url, json=payload, timeout=10)
    print('Status:', r.status_code)
    print('Response:', r.text)
except Exception as e:
    print('Error:', e)
