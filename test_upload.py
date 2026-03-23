import requests
import json
import io

url = "http://127.0.0.1:8000/upload"
csv_content = "phone\n919914643642"
files = {'file': ('test.csv', io.StringIO(csv_content))}
data = {
    'message': 'Test message from Antigravity',
    'msg_type': 'text'
}

print(f"Launching test campaign to {url}...")
try:
    response = requests.post(url, files=files, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
