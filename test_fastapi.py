import asyncio
from main import app, get_dashboard_stats, get_db
from fastapi.testclient import TestClient

client = TestClient(app)

print("Testing GET /")
response = client.get("/")
print("Status code:", response.status_code)
if response.status_code == 500:
    print("Response text:", response.text)
