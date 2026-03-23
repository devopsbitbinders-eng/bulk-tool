import requests
import json

def test_api():
    try:
        response = requests.get("http://127.0.0.1:8000/api/templates")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Templates found: {len(data)}")
            for t in data:
                print(f"- {t['name']} ({t['status']})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_api()
